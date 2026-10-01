"""
Tests for task 1.4: /api/quotes reads real quotes from the database, falls
back to clearly-labelled sample data when there are none, and exposes the
calculation steps and evidence the detail screen shows.

Run from backend/:  pytest -v
"""

import pytest
from fastapi.testclient import TestClient

import db
import main
from models import Capture, ExtractedQuote, Provider, ReferenceRate

anon = TestClient(main.app)


@pytest.fixture(autouse=True)
def client(signed_in_client):
    return signed_in_client


@pytest.fixture(autouse=True)
def empty_pipeline_tables():
    """Each test starts with no scraped data."""
    with db.connect() as conn:
        for table in ("extracted_quotes", "captures", "reference_rates", "providers"):
            conn.execute(f"DELETE FROM {table}")
    yield


def seed_wise():
    db.save_reference_rate(ReferenceRate(mid_rate=67.23, source="test source"))
    db.save_provider(Provider(id="wise", name="Wise", pricing_url="https://wise.com/fees"))
    cid = db.save_capture(Capture(provider_id="wise", url="https://wise.com/fees",
                                  content_hash="b" * 64, html_path="captures/wise/x.html"))
    db.save_quote(ExtractedQuote(
        provider_id="wise", capture_id=cid, send_amount=1000,
        fee_type="fixed", fee_amount=3.99, fee_snippet="Transfer fee: A$3.99",
        provider_rate=66.80, rate_snippet="1 AUD = 66.80 INR",
        speed_text="1-2 business days", speed_min_hours=24, speed_max_hours=48))


def test_sample_data_used_and_labelled_when_nothing_scraped(client):
    body = client.get("/api/quotes?amount=1000&to=INR").json()
    assert body["source"] == "mock"
    assert len(body["providers"]) > 0


def test_real_quotes_used_once_scraped(client):
    seed_wise()
    body = client.get("/api/quotes?amount=1000&to=INR").json()
    assert body["source"] == "database"
    assert [p["id"] for p in body["providers"]] == ["wise"]
    wise = body["providers"][0]
    assert wise["recipient_gets"] == 66533.47          # (1000 - 3.99) x 66.80
    assert wise["status"] == "fresh" and wise["badge"] == "most_received"
    assert body["mid_market_rate"]["source"] == "test source"


def test_detail_has_calculation_steps_and_evidence(client):
    seed_wise()
    body = client.get("/api/quotes/wise?amount=1000&to=INR").json()
    assert body["source"] == "database"
    steps = body["provider"]["calc_steps"]
    assert steps[-1]["step"] == "Total cost" and "696.53" in steps[-1]["result"]
    ev = body["provider"]["evidence"]
    assert ev["source_url"] == "https://wise.com/fees"
    assert ev["sha256"] == "b" * 64
    assert ev["fee_text"] == "Transfer fee: A$3.99" and ev["rate_text"] == "1 AUD = 66.80 INR"


def test_unknown_provider_is_404_and_bad_currency_is_400(client):
    seed_wise()
    assert client.get("/api/quotes/nobody?amount=1000&to=INR").status_code == 404
    assert client.get("/api/quotes?amount=1000&to=XXX").status_code == 400
