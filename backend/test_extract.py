"""
Tests for the Beautiful Soup extractor, using small hand-written pages.
Later, add real saved pages from captures/ as fixtures here.

Run from backend/:  pytest -v
"""

from extract import extract_with_selectors, find_fee, find_rate, speed_hours
from llm import relevant_slice
from models import ExtractedQuote

CFG = {"id": "sample-provider", "selectors": {"fee": None, "rate": None, "speed": None}}

FIXED_PAGE = """
<html><body>
  <script>var fee = 999;</script>
  <div class="quote">
    <p>Transfer fee: A$3.99</p>
    <p>Exchange rate: 1 AUD = 54.84 INR</p>
    <p>Arrives in 1-2 business days</p>
  </div>
</body></html>
"""


def test_fixed_fee_page_extracts_and_validates():
    data = extract_with_selectors(FIXED_PAGE, CFG, 1000)
    q = ExtractedQuote(**data)  # must pass the schema, including the evidence check
    assert (q.fee_type, q.fee_amount, q.provider_rate) == ("fixed", 3.99, 54.84)
    assert (q.speed_min_hours, q.speed_max_hours) == (24, 48)


def test_script_text_is_ignored():
    # The 999 inside <script> must never be read as a fee.
    assert extract_with_selectors(FIXED_PAGE, CFG)["fee_amount"] == 3.99


def test_selector_takes_priority():
    page = '<p>Fee from A$9.99</p><span id="our-fee">Fee A$1.50</span><p>1 AUD = 54.84 INR</p>'
    cfg = {"id": "x", "selectors": {"fee": "#our-fee"}}
    assert extract_with_selectors(page, cfg)["fee_amount"] == 1.50


def test_zero_and_percent_fees():
    assert find_fee("Send with no transfer fees today")[:2] == ("zero", 0.0)
    assert find_fee("A 1.2% fee applies")[:2] == ("percent", 1.2)


def test_rate_formats():
    assert find_rate("AUD 1 = INR 55.10")[0] == 55.10
    assert find_rate("no rate here") is None


def test_speed_parsing():
    assert speed_hours("Instantly") == (0, 1)
    assert speed_hours("Same day") == (0, 24)
    assert speed_hours("3 hours") == (3, 3)


def test_llm_slice_keeps_pricing_text_only():
    page = "About us " * 500 + "Transfer fee: A$3.99" + " Careers " * 500
    text = relevant_slice(page)
    assert "A$3.99" in text and len(text) < len(page)
