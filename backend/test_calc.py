"""
Tests for task 1.3: the calculations are correct, match the prototype,
and every result is explained step by step.

Run from backend/:  pytest -v
"""

from datetime import datetime, timedelta, timezone

import pytest

import db
from calc import build_quotes, calculate, fee_in_send_currency, status_for
from models import Capture, ExtractedQuote, Provider, ReferenceRate


def test_matches_prototype_provider_b():
    # Prototype figures: AUD 1,000, fee 5, rate 54.90, mid 55.00
    r = calculate(1000, "fixed", 5.00, 54.90, 55.00)
    assert r["amount_converted"] == 995.00
    assert r["recipient_gets"] == 54625.50
    assert r["total_cost"] == 374.50
    assert r["total_cost_pct"] == 0.68
    assert r["fx_markup_pct"] == 0.18


def test_hand_calculation_with_real_rate():
    # 1000 - 3.99 = 996.01; 996.01 x 66.80 = 66,533.47; ideal 1000 x 67.23 = 67,230
    r = calculate(1000, "fixed", 3.99, 66.80, 67.23)
    assert r["recipient_gets"] == 66533.47
    assert r["total_cost"] == 696.53
    assert r["fx_markup_pct"] == 0.64


def test_fee_types():
    assert fee_in_send_currency("fixed", 3.99, 500) == 3.99      # same at any amount
    assert fee_in_send_currency("percent", 1.2, 500) == 6.00     # scales with amount
    assert fee_in_send_currency("zero", 0, 500) == 0.0


def test_zero_fee_can_still_cost_more():
    # "No fee" but a worse rate: the markup is the real cost
    no_fee = calculate(1000, "zero", 0, 66.00, 67.23)
    with_fee = calculate(1000, "fixed", 3.99, 67.00, 67.23)
    assert no_fee["total_cost"] > with_fee["total_cost"]


def test_every_result_has_readable_steps():
    steps = calculate(1000, "fixed", 3.99, 66.80, 67.23)["calc_steps"]
    assert [s["step"] for s in steps] == [
        "Transfer fee", "Amount converted", "Recipient gets",
        "Ideal amount", "Exchange-rate markup", "Total cost",
    ]
    assert "996.01 x 66.8" in steps[2]["formula"] and "66,533.47" in steps[2]["result"]


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        calculate(10, "fixed", 12, 66.8, 67.23)  # fee bigger than amount
    with pytest.raises(ValueError):
        calculate(1000, "fixed", 3.99, 0, 67.23)


def test_freshness_rules():
    assert status_for(10) == "fresh"
    assert status_for(90) == "stale"
    assert status_for(25 * 60) == "hidden"


def test_build_quotes_from_database(tmp_path):
    path = tmp_path / "t.db"
    db.init_db(path)
    now = datetime.now(timezone.utc)
    mid = ReferenceRate(mid_rate=67.23, source="test")
    db.save_reference_rate(mid, path)

    for pid, name, fee, rate, age_h in [("a", "Alpha", 3.99, 66.80, 0), ("b", "Beta", 0, 66.00, 0),
                                        ("c", "Old", 1.00, 67.00, 30)]:
        db.save_provider(Provider(id=pid, name=name, pricing_url=f"https://example.com/{pid}"), path)
        cid = db.save_capture(Capture(provider_id=pid, url=f"https://example.com/{pid}",
                                      content_hash="a" * 64, html_path="x.html"), path)
        db.save_quote(ExtractedQuote(
            provider_id=pid, capture_id=cid, send_amount=1000,
            fee_type="zero" if fee == 0 else "fixed", fee_amount=fee,
            fee_snippet="No fee" if fee == 0 else f"Fee A${fee}",
            provider_rate=rate, rate_snippet=f"1 AUD = {rate} INR", speed_text="1-2 business days",
            speed_min_hours=24, speed_max_hours=48, extracted_at=now - timedelta(hours=age_h)), path)

    out = build_quotes(db.latest_quotes("INR", path), db.latest_mid_rate("AUD", "INR", path), 1000, now=now)
    names = [p["name"] for p in out["providers"]]
    assert names == ["Alpha", "Beta"] and out["hidden_count"] == 1       # 30 h old -> hidden
    alpha = out["providers"][0]
    assert alpha["badge"] == "most_received"
    assert alpha["evidence"]["source_url"] == "https://example.com/a"   # evidence joined from captures
    assert alpha["calc_steps"][-1]["step"] == "Total cost"
