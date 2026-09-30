"""
Transparent calculations for FeePrint.

All maths lives here, in small pure functions: no scraping, no LLM, no
database. Each quote carries `calc_steps`, a list of plain-English
steps with the formula and the numbers used, so the detail screen can
show exactly how every result was worked out.

The formulas match the prototype (data.py):
  fee_aud        = fixed fee, or amount x percent / 100, or 0
  converted      = amount - fee_aud                      (fee deducted from what's sent)
  recipient_gets = converted x provider_rate
  ideal_amount   = amount x mid_rate                     (no fee, no markup)
  total_cost     = ideal_amount - recipient_gets         (in the receive currency)
  fx_markup_pct  = (mid_rate - provider_rate) / mid_rate x 100

Assumption: fees and rates were collected for one send amount (usually
AUD 1,000). A fixed fee is assumed to stay the same at other amounts, a
percentage fee scales with the amount, and the rate is assumed not to
change with the amount. Tiered pricing isn't modelled yet.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

HIDE_AFTER_MINUTES = 24 * 60  # older than this: hidden from results
WARN_AFTER_MINUTES = 60       # older than this: shown with a "may be out of date" warning

EXTRACTOR_LABELS = {"selector": "Beautiful Soup selectors", "llm": "Gemini fallback"}


def _r(x: float) -> float:
    return round(x + 0.0, 2)


def fee_in_send_currency(fee_type: str, fee_amount: float, amount: float) -> float:
    if fee_type == "fixed":
        return _r(fee_amount)
    if fee_type == "percent":
        return _r(amount * fee_amount / 100)
    if fee_type == "zero":
        return 0.0
    raise ValueError(f"unknown fee_type {fee_type!r}")


def calculate(amount: float, fee_type: str, fee_amount: float, provider_rate: float,
              mid_rate: float, send: str = "AUD", recv: str = "INR") -> dict:
    """The core comparison for one provider, with every step written out."""
    if amount <= 0 or provider_rate <= 0 or mid_rate <= 0:
        raise ValueError("amount and rates must be positive")

    fee = fee_in_send_currency(fee_type, fee_amount, amount)
    if fee >= amount:
        raise ValueError(f"fee {fee} {send} is not less than the amount {amount} {send}")

    converted = _r(amount - fee)
    recipient_gets = _r(converted * provider_rate)
    ideal = _r(amount * mid_rate)
    total_cost = _r(ideal - recipient_gets)
    total_cost_pct = _r(total_cost / ideal * 100)
    total_cost_send = _r(total_cost / mid_rate)
    markup_pct = _r((mid_rate - provider_rate) / mid_rate * 100)

    fee_rule = {
        "fixed": f"fixed fee of {fee_amount:.2f} {send}",
        "percent": f"{fee_amount}% of {amount:,.2f} {send}",
        "zero": "no transfer fee advertised",
    }[fee_type]

    steps = [
        {"step": "Transfer fee", "formula": fee_rule, "result": f"{fee:,.2f} {send}"},
        {"step": "Amount converted", "formula": f"{amount:,.2f} - {fee:,.2f}",
         "result": f"{converted:,.2f} {send}"},
        {"step": "Recipient gets", "formula": f"{converted:,.2f} x {provider_rate} (provider rate)",
         "result": f"{recipient_gets:,.2f} {recv}"},
        {"step": "Ideal amount", "formula": f"{amount:,.2f} x {mid_rate} (mid-market rate, no fee or markup)",
         "result": f"{ideal:,.2f} {recv}"},
        {"step": "Exchange-rate markup", "formula": f"({mid_rate} - {provider_rate}) / {mid_rate} x 100",
         "result": f"{markup_pct:.2f}%"},
        {"step": "Total cost", "formula": f"{ideal:,.2f} - {recipient_gets:,.2f}",
         "result": f"{total_cost:,.2f} {recv} ({total_cost_pct:.2f}%, about {total_cost_send:,.2f} {send})"},
    ]

    return {
        "fee": fee,
        "fee_currency": send,
        "amount_converted": converted,
        "provider_rate": provider_rate,
        "recipient_gets": recipient_gets,
        "recipient_currency": recv,
        "ideal_amount": ideal,
        "fx_markup_pct": markup_pct,
        "total_cost": total_cost,
        "total_cost_pct": total_cost_pct,
        "total_cost_send_currency": total_cost_send,
        "calc_steps": steps,
    }


# ------------------------------------------------------------------ freshness

def _parse_time(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))  # 'Z' needs Python 3.11+
    t = value
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def minutes_since(value, now: datetime) -> int:
    return max(0, int((now - _parse_time(value)).total_seconds() // 60))


def status_for(minutes_ago: int) -> str:
    if minutes_ago >= HIDE_AFTER_MINUTES:
        return "hidden"
    if minutes_ago >= WARN_AFTER_MINUTES:
        return "stale"
    return "fresh"


def checked_label(minutes_ago: int) -> str:
    if minutes_ago < 60:
        return f"Checked {minutes_ago} min ago"
    return f"Checked {round(minutes_ago / 60)} h ago"


# ------------------------------------------------------------------ API response

def build_provider(row: dict, amount: float, mid_rate: float, now: datetime) -> dict:
    """One stored quote (from db.latest_quotes) -> the provider object the frontend shows."""
    send, recv = row["send_currency"], row["receive_currency"]
    result = calculate(amount, row["fee_type"], row["fee_amount"], row["provider_rate"], mid_rate, send, recv)

    minutes_ago = minutes_since(row["extracted_at"], now)
    status = status_for(minutes_ago)
    max_h = row.get("speed_max_hours")
    captured_at = row.get("captured_at") or row["extracted_at"]

    note = f"rate {row['provider_rate']} · fee deducted from amount sent"
    if row["fee_type"] == "percent":
        note = f"rate {row['provider_rate']} · {row['fee_amount']}% fee deducted from amount sent"
    if status == "stale":
        note = "price last checked over an hour ago and may have changed"

    return {
        "id": row["provider_id"],
        "name": row.get("provider_name") or row["provider_id"],
        "fee_type": row["fee_type"],
        "fee_billing": "deducted",
        **result,
        "speed_label": row["speed_text"],
        "speed_minutes_max": int(max_h * 60) if max_h is not None else None,
        "checked_at": _parse_time(row["extracted_at"]).isoformat(),
        "checked_minutes_ago": minutes_ago,
        "checked_label": checked_label(minutes_ago),
        "status": status,
        "note": note,
        "badge": None,
        "evidence": {
            "source_url": row.get("source_url") or row.get("pricing_url"),
            "captured_at": _parse_time(captured_at).isoformat(),
            "sha256": row.get("content_hash") or "",
            "fee_text": row["fee_snippet"],
            "rate_text": row["rate_snippet"],
            "retention_until": (_parse_time(captured_at) + timedelta(days=365)).date().isoformat(),
            "parser_version": EXTRACTOR_LABELS.get(row["method"], row["method"]),
        },
    }


def build_quotes(rows: list[dict], mid: dict, amount: float, to_country: str = "India",
                 method: str = "bank_transfer", now: datetime | None = None) -> dict:
    """All stored quotes for a corridor -> the /api/quotes response (same shape as the prototype)."""
    now = now or datetime.now(timezone.utc)
    mid_rate = mid["mid_rate"]
    send, recv = mid["base_currency"], mid["quote_currency"]

    built = [build_provider(r, amount, mid_rate, now) for r in rows]
    visible = [b for b in built if b["status"] != "hidden"]
    hidden = [b for b in built if b["status"] == "hidden"]

    if visible:
        max(visible, key=lambda b: b["recipient_gets"])["badge"] = "most_received"
    for b in visible:
        if b["badge"] is None:
            if b["status"] == "stale":
                b["badge"] = "stale_warning"
            elif b["fee"] == 0:
                b["badge"] = "zero_fee_notice"

    return {
        "corridor": {"from_currency": send, "to_currency": recv, "to_country": to_country,
                     "amount": amount, "method": method},
        "mid_market_rate": {"rate": mid_rate, "as_of": _parse_time(mid["fetched_at"]).isoformat(),
                            "source": mid.get("source")},
        "ideal_amount": _r(amount * mid_rate),
        "providers": visible,
        "hidden_count": len(hidden),
        "hidden_reason": "data more than 24 hours old" if hidden else None,
        "generated_at": now.isoformat(),
    }
