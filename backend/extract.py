"""
Primary extractor: Beautiful Soup.

For each value (fee, rate, speed) we read the text of the provider's CSS
selector if one is configured, otherwise the whole visible page, and
pull the value out with a pattern. The result is a plain dict that must
still pass the ExtractedQuote schema before it's stored.
"""

import re

from bs4 import BeautifulSoup

NUM = r"\d[\d,]*(?:\.\d+)?"
MONEY = r"(?:A\$|AU\$|AUD\s?|\$)"


class ExtractionError(Exception):
    """Raised when a required value (fee or rate) can't be found."""


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _window(text: str, start: int, end: int, pad: int = 40) -> str:
    """The matched text plus a little context either side, as evidence."""
    return text[max(0, start - pad): end + pad].strip()


def _soup(html) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser") if isinstance(html, str) else html
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return soup


def visible_text(html) -> str:
    """All human-visible text on the page, whitespace tidied."""
    return re.sub(r"\s+", " ", _soup(html).get_text(" ")).strip()


def _selected_text(soup: BeautifulSoup, css: str | None) -> str | None:
    if not css:
        return None
    el = soup.select_one(css)
    return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else None


# ------------------------------------------------------------------ finders

def find_fee(text: str, send_amount: float | None = None):
    """Returns (fee_type, amount, snippet) or None. Checks fixed, then percent, then zero.

    Matches that can't be a real fee are skipped (a fixed fee over 10% of the amount,
    a percentage over 10) so promo text like "transfer up to A$1,000" isn't misread."""
    patterns = [
        ("fixed", rf"(?:transfer\s+)?fees?\b[^0-9%]{{0,40}}?{MONEY}\s?({NUM})"),
        ("fixed", rf"{MONEY}\s?({NUM})\s*(?:transfer\s+)?fee"),
        ("percent", rf"({NUM})\s*%\s*(?:transfer\s+)?fee"),
        ("percent", rf"fees?\b[^0-9%]{{0,40}}?({NUM})\s*%"),
    ]
    for fee_type, pat in patterns:
        for m in re.finditer(pat, text, re.I):
            amount = _num(m.group(1))
            if fee_type == "percent" and amount > 10:
                continue
            if fee_type == "fixed" and send_amount and amount > 0.10 * send_amount:
                continue
            return fee_type, amount, _window(text, m.start(), m.end())
    m = re.search(r"\b(?:no|zero)\s+(?:transfer\s+)?fees?\b|\b0\s+fees?\b", text, re.I)
    if m:
        return "zero", 0.0, _window(text, m.start(), m.end())
    return None


def find_fee_regex(text: str, pattern: str):
    """Provider-specific fee: `pattern` has one group capturing the AUD amount,
    e.g. r"Bank transfer\\s+(\\d[\\d,]*(?:\\.\\d+)?)\\s*AUD". 0 becomes a 'zero' fee."""
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    amount = _num(m.group(1))
    return ("zero" if amount == 0 else "fixed"), amount, _window(text, m.start(), m.end(), pad=25)


def find_rate(text: str, send: str = "AUD", recv: str = "INR"):
    """Returns (rate, snippet) or None. Matches '1 AUD = 54.84 INR' and 'AUD 1 = INR 54.84'."""
    patterns = [
        rf"1(?:\.0+)?\s*{send}\s*=\s*({NUM})\s*{recv}",
        rf"{send}\s*1(?:\.0+)?\s*=\s*{recv}\s*({NUM})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return _num(m.group(1)), _window(text, m.start(), m.end(), pad=20)
    return None


SPEED_RE = re.compile(
    r"instant(?:ly)?|in\s+seconds|within\s+minutes|in\s+minutes|same[\s-]day|next[\s-]day|"
    r"\d+\s*(?:-|–|to)\s*\d+\s*(?:business\s+|working\s+)?(?:days|hours)|"
    r"\d+\s*(?:business\s+|working\s+)?(?:days?|hours?|minutes?)",
    re.I,
)


def find_speed(text: str) -> str | None:
    m = SPEED_RE.search(text)
    return m.group(0) if m else None


def speed_hours(speed: str | None) -> tuple[float | None, float | None]:
    """'1-2 business days' -> (24, 48). Unknown wording -> (None, None)."""
    if not speed:
        return None, None
    s = speed.lower()
    if "instant" in s or "second" in s or "minute" in s:
        return 0.0, 1.0
    if "same" in s:
        return 0.0, 24.0
    if "next" in s:
        return 24.0, 48.0
    nums = [float(n) for n in re.findall(r"\d+", s)]
    if not nums:
        return None, None
    unit = 24.0 if "day" in s else 1.0
    return min(nums) * unit, max(nums) * unit


# ------------------------------------------------------------------ main entry

def extract_with_selectors(html, cfg: dict, send_amount: float = 1000.0,
                           send: str = "AUD", recv: str = "INR") -> dict:
    soup = _soup(html)
    page = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    sel = cfg.get("selectors", {})

    fee_text = _selected_text(soup, sel.get("fee")) or page
    fee = None
    if cfg.get("fee_regex"):
        fee = find_fee_regex(fee_text, cfg["fee_regex"])
    fee = fee or find_fee(fee_text, send_amount)
    rate = find_rate(_selected_text(soup, sel.get("rate")) or page, send, recv)
    speed = find_speed(_selected_text(soup, sel.get("speed")) or page)

    missing = [name for name, value in (("fee", fee), ("rate", rate)) if value is None]
    if missing:
        raise ExtractionError(f"could not find {' and '.join(missing)} on the page")

    fee_type, fee_amount, fee_snippet = fee
    provider_rate, rate_snippet = rate
    min_h, max_h = speed_hours(speed)
    return dict(
        provider_id=cfg["id"],
        send_currency=send,
        receive_currency=recv,
        send_amount=send_amount,
        fee_type=fee_type,
        fee_amount=fee_amount,
        fee_snippet=fee_snippet,
        provider_rate=provider_rate,
        rate_snippet=rate_snippet,
        speed_text=speed or "Not stated on page",
        speed_min_hours=min_h,
        speed_max_hours=max_h,
        method="selector",
    )
