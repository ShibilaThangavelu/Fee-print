"""
SQLite storage for FeePrint's collection pipeline.

Tables (the `users` table is created separately by auth.py):
  providers         who we collect from, and which extractor to use
  captures          every page load: URL, time, SHA-256 hash, saved HTML (the evidence)
  extracted_quotes  normalised fee / rate / speed pulled from one capture
  reference_rates   mid-market rates each quote is compared against

The CHECK constraints repeat the most important Pydantic rules, so bad
data is refused even if something skips the models.

Run `python db.py` to create the tables. It's safe to run more than once.
In AWS these tables become DynamoDB (Quotes, ReferenceRates) and S3 (HTML).
"""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from models import Capture, ExtractedQuote, Provider, ReferenceRate


def db_path() -> Path:
    return Path(os.getenv("FEEPRINT_DB", Path(__file__).with_name("feeprint.db")))


SCHEMA = """
CREATE TABLE IF NOT EXISTS providers (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    pricing_url  TEXT NOT NULL,
    extractor    TEXT NOT NULL DEFAULT 'selector' CHECK (extractor IN ('selector', 'llm'))
);

CREATE TABLE IF NOT EXISTS captures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id  TEXT NOT NULL REFERENCES providers(id),
    url          TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    html_path    TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('ok', 'failed'))
);

CREATE TABLE IF NOT EXISTS extracted_quotes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id      TEXT NOT NULL REFERENCES providers(id),
    capture_id       INTEGER REFERENCES captures(id),
    send_currency    TEXT NOT NULL,
    receive_currency TEXT NOT NULL,
    send_amount      REAL NOT NULL CHECK (send_amount > 0),
    fee_type         TEXT NOT NULL CHECK (fee_type IN ('fixed', 'percent', 'zero')),
    fee_amount       REAL NOT NULL CHECK (fee_amount >= 0),
    provider_rate    REAL NOT NULL CHECK (provider_rate > 0),
    speed_text       TEXT NOT NULL,
    speed_min_hours  REAL,
    speed_max_hours  REAL,
    fee_snippet      TEXT NOT NULL,
    rate_snippet     TEXT NOT NULL,
    method           TEXT NOT NULL CHECK (method IN ('selector', 'llm')),
    extracted_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quotes_latest
    ON extracted_quotes (receive_currency, provider_id, extracted_at);

CREATE TABLE IF NOT EXISTS reference_rates (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    base_currency  TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    mid_rate       REAL NOT NULL CHECK (mid_rate > 0),
    source         TEXT NOT NULL,
    fetched_at     TEXT NOT NULL
);
"""


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path=None) -> None:
    with closing(connect(path)) as conn:
        conn.executescript(SCHEMA)


def _insert(conn: sqlite3.Connection, table: str, row: dict) -> int:
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(row.values()))
    return cur.lastrowid


# ------------------------------------------------------------------ writes
# Each takes a validated model, so nothing unchecked reaches the database.

def save_provider(p: Provider, path=None) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute(
            """INSERT INTO providers (id, name, pricing_url, extractor) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name = excluded.name, pricing_url = excluded.pricing_url, extractor = excluded.extractor""",
            (p.id, p.name, str(p.pricing_url), p.extractor),
        )


def save_capture(c: Capture, path=None) -> int:
    with closing(connect(path)) as conn, conn:
        return _insert(conn, "captures", c.model_dump(mode="json"))


def save_quote(q: ExtractedQuote, path=None) -> int:
    with closing(connect(path)) as conn, conn:
        return _insert(conn, "extracted_quotes", q.model_dump(mode="json"))


def save_reference_rate(r: ReferenceRate, path=None) -> int:
    with closing(connect(path)) as conn, conn:
        return _insert(conn, "reference_rates", r.model_dump(mode="json"))


# ------------------------------------------------------------------ reads

def latest_quotes(receive_currency: str = "INR", path=None) -> list[dict]:
    """The most recent quote per provider for one corridor, with provider details."""
    with closing(connect(path)) as conn:
        rows = conn.execute(
            """SELECT q.*, p.name AS provider_name, p.pricing_url
               FROM extracted_quotes q
               JOIN providers p ON p.id = q.provider_id
               WHERE q.receive_currency = ?
                 AND q.extracted_at = (
                     SELECT MAX(extracted_at) FROM extracted_quotes
                     WHERE provider_id = q.provider_id AND receive_currency = q.receive_currency)
               ORDER BY p.name""",
            (receive_currency.upper(),),
        ).fetchall()
    return [dict(r) for r in rows]


def latest_mid_rate(base: str = "AUD", quote: str = "INR", path=None) -> dict | None:
    with closing(connect(path)) as conn:
        row = conn.execute(
            """SELECT * FROM reference_rates
               WHERE base_currency = ? AND quote_currency = ?
               ORDER BY fetched_at DESC LIMIT 1""",
            (base.upper(), quote.upper()),
        ).fetchone()
    return dict(row) if row else None


if __name__ == "__main__":
    init_db()
    with closing(connect()) as conn:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
    print(f"Database: {db_path()}")
    print("Tables:  ", ", ".join(tables))
