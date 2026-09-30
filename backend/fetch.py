"""
Playwright's job: load the provider page properly (including prices
that JavaScript fills in), then hand back the rendered HTML.

Every page we read is saved to captures/<provider>/<time>.html with a
SHA-256 hash, so each number FeePrint shows can be traced to the exact
page it came from.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

CAPTURE_DIR = Path(__file__).with_name("captures")

# A normal browser identity, plus an honest note of who we are.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 FeePrint/0.1 (student project)"
)


def fetch_page(cfg: dict, amount: float = 1000, headless: bool = True) -> tuple[str, str]:
    """Open cfg["pricing_url"], optionally type the amount, return (html, final_url)."""
    # Imported here so re-running extraction on saved pages doesn't need a browser.
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(
                user_agent=USER_AGENT, locale="en-AU", timezone_id="Australia/Melbourne"
            )
            page = context.new_page()
            page.goto(cfg["pricing_url"], wait_until="domcontentloaded", timeout=45_000)

            if cfg.get("amount_input"):
                box = page.locator(cfg["amount_input"]).first
                box.fill("")
                box.type(str(int(amount)), delay=50)  # type like a person so the page recalculates

            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except PlaywrightTimeout:
                pass  # some sites never go fully idle; carry on with what has loaded

            if cfg.get("wait_for"):
                page.wait_for_selector(cfg["wait_for"], timeout=15_000)

            return page.content(), page.url
        finally:
            browser.close()


def save_capture_file(provider_id: str, html: str) -> tuple[str, str]:
    """Save the rendered HTML as evidence. Returns (path, sha256)."""
    now = datetime.now(timezone.utc)
    folder = CAPTURE_DIR / provider_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now:%Y%m%dT%H%M%SZ}.html"
    path.write_text(html, encoding="utf-8")
    return str(path), hashlib.sha256(html.encode("utf-8")).hexdigest()
