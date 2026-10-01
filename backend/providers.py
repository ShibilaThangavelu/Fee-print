"""
Which providers FeePrint collects from, and how to read each one.

To add or tune a provider, open its pricing page in Chrome, right-click
the fee / rate / delivery-time text -> Inspect, and copy a stable CSS
selector into "selectors". Leave a selector as None and the extractor
falls back to finding that value by text pattern (e.g. "1 AUD = 54.84 INR").

Only add providers your mentor has approved, and check each site's
robots.txt and terms of use first.
"""

PROVIDERS = [
    {
        "id": "wise",
        "name": "Wise",
        # Check this opens the AUD -> INR page in your browser.
        "pricing_url": "https://wise.com/au/send-money/send-money-to-india",
        "amount_input": None,  # CSS selector of the "You send" box, if an amount must be typed
        "wait_for": None,      # CSS selector that appears once prices have loaded
        "selectors": {"fee": None, "rate": None, "speed": None},
        # Wise lists a fee per pay-in method; we compare the bank transfer one.
        "fee_regex": r"Bank transfer\s+(\d[\d,]*(?:\.\d+)?)\s*AUD",
    },
    {
        "id": "remitly",
        "name": "Remitly",
        "pricing_url": "https://www.remitly.com/au/en/india",
        "amount_input": None,
        "wait_for": None,
        "selectors": {"fee": None, "rate": None, "speed": None},
    },
    # Add once your mentor confirms scraping CommBank is OK:
    # {
    #     "id": "commbank",
    #     "name": "CommBank",
    #     "pricing_url": "https://www.commbank.com.au/...",
    #     "amount_input": None,
    #     "wait_for": None,
    #     "selectors": {"fee": None, "rate": None, "speed": None},
    # },
]
