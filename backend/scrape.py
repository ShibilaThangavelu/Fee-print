"""
Collect prices for every provider in providers.py:

  fetch (Playwright) -> save evidence -> extract (Beautiful Soup, Gemini fallback)
  -> validate (schema + within 5% of mid-market) -> store in SQLite

Usage (from backend/, with the venv active):
  python scrape.py                                   # all providers
  python scrape.py --provider wise                   # one provider
  python scrape.py --provider wise --show            # watch the browser work
  python scrape.py --provider wise --html captures/wise/<file>.html --force-llm
        # test the Gemini fallback on a saved page (nothing stored)
  python scrape.py --provider wise --html captures/wise/<file>.html
        # re-run extraction on a saved page: no browser, nothing stored
"""

import argparse
import hashlib
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # GEMINI_API_KEY, GEMINI_MODEL from backend/.env

from pydantic import ValidationError  # noqa: E402

import db  # noqa: E402
from extract import ExtractionError, extract_with_selectors, visible_text  # noqa: E402
from fetch import fetch_page, save_capture_file  # noqa: E402
from llm import llm_extract  # noqa: E402
from models import Capture, ExtractedQuote, Provider, ReferenceRate, check_against_mid  # noqa: E402
from providers import PROVIDERS  # noqa: E402
from observability import flush, init_sentry, report_scrape_failure  # noqa: E402
from rates import fetch_mid_rate  # noqa: E402


def _short(err: Exception) -> str:
    return str(err).splitlines()[0][:200]


def run_provider(cfg: dict, amount: float, mid: ReferenceRate | None,
                 html_file: str | None = None, headless: bool = True,
                 force_llm: bool = False) -> bool:
    print(f"\n{cfg['name']}")
    dry_run = html_file is not None

    # 1. Get the page
    if dry_run:
        html = Path(html_file).read_text(encoding="utf-8")
        capture_id = None
    else:
        db.save_provider(Provider(id=cfg["id"], name=cfg["name"], pricing_url=cfg["pricing_url"]))
        try:
            html, final_url = fetch_page(cfg, amount, headless=headless)
        except Exception as e:
            print(f"  FAIL  could not load page: {_short(e)}")
            report_scrape_failure(cfg["id"], f"could not load page: {_short(e)}")
            return False
        path, sha = save_capture_file(cfg["id"], html)
        capture_id = db.save_capture(
            Capture(provider_id=cfg["id"], url=final_url, content_hash=sha, html_path=path)
        )
        print(f"  saved evidence: {path}")

    # 2. Extract: Beautiful Soup first, Gemini only if that fails
    try:
        if force_llm:
            raise ExtractionError("skipped on purpose (--force-llm)")
        quote = ExtractedQuote(**extract_with_selectors(html, cfg, amount), capture_id=capture_id)
        print("  OK    extracted with Beautiful Soup")
    except (ExtractionError, ValidationError) as e:
        print(f"  ..    Beautiful Soup couldn't: {_short(e)}")
        try:
            data = llm_extract(visible_text(html), cfg["id"], amount)
            quote = ExtractedQuote(**data, capture_id=capture_id)
            print("  OK    extracted with Gemini fallback")
        except Exception as e2:
            print(f"  FAIL  Gemini fallback: {_short(e2)}")
            report_scrape_failure(cfg["id"], f"extraction failed: {_short(e2)}")
            return False

    # 3. Cross-check against the mid-market rate
    if mid:
        problems = check_against_mid(quote, mid)
        if problems:
            print(f"  FAIL  rejected: {'; '.join(problems)}")
            report_scrape_failure(cfg["id"], f"rejected: {'; '.join(problems)}")
            return False

    fee = {"fixed": f"A${quote.fee_amount:.2f}", "percent": f"{quote.fee_amount}%", "zero": "no fee"}
    print(f"        fee:   {fee[quote.fee_type]}   <- \"{quote.fee_snippet}\"")
    print(f"        rate:  1 AUD = {quote.provider_rate} INR   <- \"{quote.rate_snippet}\"")
    print(f"        speed: {quote.speed_text}")

    # 4. Store
    if not dry_run:
        db.save_quote(quote)
    return True


def main():
    ap = argparse.ArgumentParser(description="Collect FeePrint provider prices.")
    ap.add_argument("--provider", help="only this provider id")
    ap.add_argument("--amount", type=float, default=1000.0, help="AUD to send (default 1000)")
    ap.add_argument("--html", help="re-run extraction on a saved page (needs --provider)")
    ap.add_argument("--show", action="store_true", help="show the browser window")
    ap.add_argument("--force-llm", action="store_true", help="skip Beautiful Soup and test the Gemini fallback")
    args = ap.parse_args()

    targets = [p for p in PROVIDERS if not args.provider or p["id"] == args.provider]
    if not targets:
        sys.exit(f"Unknown provider {args.provider!r}. Options: {', '.join(p['id'] for p in PROVIDERS)}")
    if args.html and len(targets) != 1:
        sys.exit("--html needs --provider")

    init_sentry("scraper")
    db.init_db()
    mid = None
    try:
        mid = fetch_mid_rate()
        print(f"Mid-market AUD -> INR: {mid.mid_rate}  ({mid.source})")
        if not args.html:
            db.save_reference_rate(mid)
    except Exception as e:
        print(f"Warning: couldn't get the mid-market rate ({_short(e)}); skipping the 5% check.")

    ok = sum(run_provider(cfg, args.amount, mid, args.html, headless=not args.show, force_llm=args.force_llm) for cfg in targets)
    print(f"\n{ok} of {len(targets)} providers stored" + (" (dry run)" if args.html else ""))
    flush()


if __name__ == "__main__":
    main()
