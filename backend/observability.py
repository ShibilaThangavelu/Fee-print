"""
Sentry setup shared by the API and the scraper. Does nothing unless SENTRY_DSN is set,
so the app runs fine without an account.
"""

import os


def init_sentry(service: str) -> bool:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("FEEPRINT_ENV", "local"),
        traces_sample_rate=0.1,   # 10% of requests get performance traces
        send_default_pii=False,   # never send emails, IPs or cookies
    )
    sentry_sdk.set_tag("service", service)
    return True


def report_scrape_failure(provider_id: str, reason: str) -> None:
    """Tell Sentry a provider could not be read, tagged so you can filter by provider."""
    if not os.getenv("SENTRY_DSN"):
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        scope.set_tag("provider", provider_id)
        scope.set_tag("event", "scrape_failed")
        sentry_sdk.capture_message(f"Scrape failed for {provider_id}: {reason}", level="warning")


def flush() -> None:
    if os.getenv("SENTRY_DSN"):
        import sentry_sdk

        sentry_sdk.flush(timeout=5)
