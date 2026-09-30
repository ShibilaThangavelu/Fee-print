"""
Mock provider data + the normalisation/calculation logic for FeePrint.

This mirrors the shape the real pipeline would produce after the
extract -> normalise -> validate Lambdas have run: every provider is
reduced to the same handful of fields (fee, fx markup %, speed,
checked_at) no matter how each one actually advertises its pricing.

Everything here is fabricated for the prototype. In production this
data comes from the Providers / Quotes tables, not from a Python dict.
"""

from datetime import datetime, timedelta, timezone

# Sydney is UTC+10 (ignoring DST for this mock).
SYDNEY_TZ = timezone(timedelta(hours=10))

# Mid-market reference rates, keyed by destination currency.
# In production these come from the licensed FX reference feed via the
# ReferenceRates table, refreshed every 10 minutes.
MID_MARKET_RATES = {
    "INR": {"rate": 55.00, "country": "India", "name": "Indian rupee"},
    "PHP": {"rate": 31.20, "country": "Philippines", "name": "Philippine peso"},
    "CNY": {"rate": 4.55, "country": "China", "name": "Chinese yuan"},
    "VND": {"rate": 15250.00, "country": "Vietnam", "name": "Vietnamese dong"},
    "GBP": {"rate": 0.51, "country": "United Kingdom", "name": "Pound sterling"},
}

# Raw, per-provider inputs. fee is in the SEND currency (AUD).
# fx_markup_pct is how far below the mid-market rate this provider's
# rate sits. fee_billing describes how the provider presents the fee
# (this only changes the explanation text shown to the user - the
# comparison math treats every fee the same way: it comes out of the
# amount the user handed over).
_PROVIDERS = [
    {
        "id": "provider-b",
        "name": "Provider B",
        "fee": 5.00,
        "fee_billing": "deducted",
        "fx_markup_pct": 0.18,
        "speed_label": "Minutes",
        "speed_minutes_max": 30,
        "checked_minutes_ago": 25,
        "parser_version": "provider-b v1.4",
    },
    {
        "id": "provider-d",
        "name": "Provider D",
        "fee": 3.00,
        "fee_billing": "deducted",
        "fx_markup_pct": 0.45,
        "speed_label": "Same day",
        "speed_minutes_max": 720,
        "checked_minutes_ago": 40,
        "parser_version": "provider-d v1.1",
    },
    {
        "id": "provider-e",
        "name": "Provider E",
        "fee": 0.00,
        "fee_billing": "deducted",
        "fx_markup_pct": 1.00,
        "speed_label": "1–2 business days",
        "speed_minutes_max": 2880,
        "checked_minutes_ago": 180,
        "parser_version": "provider-e v2.0",
        "last_check_failed": True,
    },
    {
        "id": "provider-c",
        "name": "Provider C",
        "fee": 12.00,
        "fee_billing": "added_on_top",
        "fx_markup_pct": 0.09,
        "speed_label": "Minutes",
        "speed_minutes_max": 30,
        "checked_minutes_ago": 12,
        "parser_version": "provider-c v1.0",
    },
    {
        "id": "provider-a",
        "name": "Provider A",
        "fee": 0.00,
        "fee_billing": "deducted",
        "fx_markup_pct": 1.45,
        "speed_label": "Minutes",
        "speed_minutes_max": 30,
        "checked_minutes_ago": 18,
        "parser_version": "provider-a v1.2",
    },
    {
        # Deliberately stale so the API demonstrates the "hidden after
        # 24h" rule described on the results screen.
        "id": "provider-f",
        "name": "Provider F",
        "fee": 2.00,
        "fee_billing": "deducted",
        "fx_markup_pct": 0.60,
        "speed_label": "Same day",
        "speed_minutes_max": 720,
        "checked_minutes_ago": 1500,
        "parser_version": "provider-f v1.0",
    },
]

HIDE_AFTER_MINUTES = 24 * 60
WARN_AFTER_MINUTES = 60


def _checked_label(minutes_ago: int) -> str:
    if minutes_ago < 60:
        return f"Checked {minutes_ago} min ago"
    hours = round(minutes_ago / 60)
    return f"Checked {hours} h ago"


def _status_for(minutes_ago: int, last_check_failed: bool) -> str:
    if minutes_ago >= HIDE_AFTER_MINUTES:
        return "hidden"
    if minutes_ago >= WARN_AFTER_MINUTES or last_check_failed:
        return "stale"
    return "fresh"


def get_supported_currencies():
    return [
        {"code": code, "country": v["country"], "name": v["name"]}
        for code, v in MID_MARKET_RATES.items()
    ]


def _build_provider(p, amount, mid_rate, ideal_amount, now):
    # Round the rate to the same 2 decimals a provider would advertise
    # before converting - this matches how the comparison is explained
    # to the user step by step on the calculation screen.
    provider_rate = round(mid_rate * (1 - p["fx_markup_pct"] / 100), 2)
    converted = round(amount - p["fee"], 2)
    recipient_gets = round(converted * provider_rate, 2)
    total_cost = round(ideal_amount - recipient_gets, 2)
    total_cost_pct = round((total_cost / ideal_amount) * 100, 2) if ideal_amount else 0

    checked_minutes_ago = p["checked_minutes_ago"]
    checked_at = now - timedelta(minutes=checked_minutes_ago)
    status = _status_for(checked_minutes_ago, p.get("last_check_failed", False))

    if p["fee_billing"] == "added_on_top":
        note = (
            f"rate {provider_rate:.2f} · fee is added on top, so we show it as "
            f"the full amount to compare fairly"
        )
    else:
        note = f"rate {provider_rate:.2f} · fee deducted from amount sent"

    if status == "stale":
        note = "our last check of this provider failed, so this is the last confirmed price" \
            if p.get("last_check_failed") else note

    return {
        "id": p["id"],
        "name": p["name"],
        "fee": p["fee"],
        "fee_currency": "AUD",
        "fee_billing": p["fee_billing"],
        "fx_markup_pct": p["fx_markup_pct"],
        "provider_rate": provider_rate,
        "amount_converted": converted,
        "recipient_gets": recipient_gets,
        "recipient_currency": None,  # filled by caller
        "total_cost": total_cost,
        "total_cost_pct": total_cost_pct,
        "speed_label": p["speed_label"],
        "speed_minutes_max": p["speed_minutes_max"],
        "checked_at": checked_at.isoformat(),
        "checked_minutes_ago": checked_minutes_ago,
        "checked_label": _checked_label(checked_minutes_ago),
        "status": status,
        "note": note,
        "badge": None,  # filled in by caller once ranking is known
        "evidence": {
            "source_url": f"https://example.com/{p['id']}/pricing",
            "captured_at": (checked_at + timedelta(minutes=10)).isoformat(),
            "sha256": "9f3c1a7d2b6e4f08b1d5c9a3e7f21b6d4c8a0f5e2d9b7c1a3f6e8d0c2b4a9e21a"[:4]
            + "…"
            + "e21a",
            "retention_until": (checked_at.replace(year=checked_at.year + 1)).date().isoformat(),
            "parser_version": p["parser_version"],
        },
    }


def build_quotes(amount: float, to_currency: str, method: str = "bank_transfer"):
    to_currency = (to_currency or "INR").upper()
    rate_info = MID_MARKET_RATES.get(to_currency, MID_MARKET_RATES["INR"])
    mid_rate = rate_info["rate"]
    ideal_amount = round(amount * mid_rate, 2)
    now = datetime.now(SYDNEY_TZ)

    built = [_build_provider(p, amount, mid_rate, ideal_amount, now) for p in _PROVIDERS]
    for b in built:
        b["recipient_currency"] = to_currency

    visible = [b for b in built if b["status"] != "hidden"]
    hidden = [b for b in built if b["status"] == "hidden"]

    if visible:
        best = max(visible, key=lambda b: b["recipient_gets"])
        best["badge"] = "most_received"
    for b in visible:
        if b["badge"] is not None:
            continue
        if b["status"] == "stale":
            b["badge"] = "stale_warning"
        elif b["fee"] == 0:
            b["badge"] = "zero_fee_notice"

    return {
        "corridor": {
            "from_currency": "AUD",
            "to_currency": to_currency,
            "to_country": rate_info["country"],
            "amount": amount,
            "method": method,
        },
        "mid_market_rate": {
            "rate": mid_rate,
            "as_of": now.replace(minute=(now.minute // 10) * 10, second=0, microsecond=0).isoformat(),
        },
        "ideal_amount": ideal_amount,
        "providers": visible,
        "hidden_count": len(hidden),
        "hidden_reason": "data more than 24 hours old" if hidden else None,
        "generated_at": now.isoformat(),
    }


def get_provider_quote(provider_id: str, amount: float, to_currency: str, method: str = "bank_transfer"):
    data = build_quotes(amount, to_currency, method)
    for p in data["providers"]:
        if p["id"] == provider_id:
            return data, p
    return data, None
