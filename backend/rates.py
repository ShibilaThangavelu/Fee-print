"""
Mid-market reference rate, used to check each provider's rate is
plausible (within 5%) and later to calculate the exchange-rate markup.

Source: Frankfurter (free, no key), which publishes the European Central
Bank's daily reference rates. It updates once per working day, so it's
a daily reference, not a live mid-market rate.
"""

import requests

from models import ReferenceRate

URL = "https://api.frankfurter.app/latest"


def fetch_mid_rate(base: str = "AUD", quote: str = "INR") -> ReferenceRate:
    r = requests.get(URL, params={"from": base, "to": quote}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return ReferenceRate(
        base_currency=base,
        quote_currency=quote,
        mid_rate=data["rates"][quote],
        source=f"Frankfurter / ECB reference rate for {data['date']}",
    )
