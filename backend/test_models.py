"""
Tests for task 1.1: the schema accepts a good quote, rejects bad ones,
and a quote survives a round trip through SQLite.

Run from backend/:  pytest -v
Uses a temporary database, so your real feeprint.db is never touched.
"""

import sqlite3

import pytest
from pydantic import ValidationError

import db
from models import ExtractedQuote, Provider, ReferenceRate, check_against_mid


def sample(**overrides) -> dict:
    """A hand-typed quote, as if read from a provider page."""
    data = dict(
        provider_id="sample-provider",
        send_amount=1000,
        fee_type="fixed",
        fee_amount=3.99,
        provider_rate=54.84,
        speed_text="Arrives in 1-2 business days",
        speed_min_hours=24,
        speed_max_hours=48,
        fee_snippet="Transfer fee: A$3.99",
        rate_snippet="1 AUD = 54.84 INR",
    )
    data.update(overrides)
    return data


# ------------------------------------------------------------ schema rules

def test_valid_quote_passes():
    q = ExtractedQuote(**sample())
    assert q.fee_amount == 3.99 and q.receive_currency == "INR"


def test_negative_fee_rejected():
    with pytest.raises(ValidationError):
        ExtractedQuote(**sample(fee_amount=-5))


def test_zero_fee_type_must_have_zero_amount():
    ExtractedQuote(**sample(fee_type="zero", fee_amount=0, fee_snippet="No transfer fee"))
    with pytest.raises(ValidationError):
        ExtractedQuote(**sample(fee_type="zero", fee_amount=2))


def test_percent_fee_over_limit_rejected():
    with pytest.raises(ValidationError):
        ExtractedQuote(**sample(fee_type="percent", fee_amount=15, fee_snippet="15% fee"))


def test_fee_must_appear_in_its_snippet():
    # Extractor says 3.99, but the page text says 4.99: reject.
    with pytest.raises(ValidationError):
        ExtractedQuote(**sample(fee_snippet="Transfer fee: A$4.99"))


def test_unknown_field_rejected():
    # e.g. an LLM adding a field we never asked for
    with pytest.raises(ValidationError):
        ExtractedQuote(**sample(bonus_offer=True))


def test_rate_far_from_mid_market_flagged():
    mid = ReferenceRate(mid_rate=55.00, source="test")
    assert check_against_mid(ExtractedQuote(**sample()), mid) == []
    bad = ExtractedQuote(**sample(provider_rate=45.0, rate_snippet="1 AUD = 45.0 INR"))
    assert check_against_mid(bad, mid)  # 18% away -> problem reported


# ------------------------------------------------------------ database

@pytest.fixture
def tmp_db(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)
    db.save_provider(
        Provider(id="sample-provider", name="Sample Provider", pricing_url="https://example.com/fees"),
        path,
    )
    return path


def test_quote_round_trip(tmp_db):
    db.save_quote(ExtractedQuote(**sample()), tmp_db)
    rows = db.latest_quotes("INR", tmp_db)
    assert len(rows) == 1
    assert rows[0]["fee_amount"] == 3.99
    assert rows[0]["provider_name"] == "Sample Provider"


def test_database_refuses_negative_fee_even_without_pydantic(tmp_db):
    with pytest.raises(sqlite3.IntegrityError):
        with db.connect(tmp_db) as conn:
            conn.execute(
                """INSERT INTO extracted_quotes
                   (provider_id, send_currency, receive_currency, send_amount, fee_type,
                    fee_amount, provider_rate, speed_text, fee_snippet, rate_snippet,
                    method, extracted_at)
                   VALUES ('sample-provider', 'AUD', 'INR', 1000, 'fixed',
                           -5, 54.84, 'x', 'x', 'x', 'selector', '2026-09-30')"""
            )
