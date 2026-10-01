"""Task 2.1: comparing providers needs an account."""

from fastapi.testclient import TestClient

import main

PW = "password123"


def fresh():
    return TestClient(main.app)


def test_quotes_require_sign_in():
    c = fresh()
    assert c.get("/api/quotes?amount=1000&to=INR").status_code == 401
    assert c.get("/api/quotes/wise?amount=1000&to=INR").status_code == 401


def test_public_rate_needs_no_account_and_has_no_providers():
    body = fresh().get("/api/rate?to=INR").json()
    assert "mid_market_rate" in body and "providers" not in body


def test_signup_unlocks_quotes_and_signout_locks_them_again():
    c = fresh()
    r = c.post("/api/auth/signup", json={"name": "Ann", "email": "ann@example.com", "password": PW})
    assert r.status_code == 201
    assert c.get("/api/quotes?amount=1000&to=INR").status_code == 200
    assert c.get("/api/auth/me").json()["user"]["email"] == "ann@example.com"
    c.post("/api/auth/signout")
    assert c.get("/api/auth/me").json()["user"] is None
    assert c.get("/api/quotes?amount=1000&to=INR").status_code == 401


def test_duplicate_email_and_wrong_password_are_rejected():
    c = fresh()
    c.post("/api/auth/signup", json={"name": "Bo", "email": "bo@example.com", "password": PW})
    assert fresh().post("/api/auth/signup", json={"name": "Bo", "email": "bo@example.com", "password": PW}).status_code >= 400
    assert fresh().post("/api/auth/signin", json={"email": "bo@example.com", "password": "wrong-pass"}).status_code == 401
    assert fresh().post("/api/auth/signin", json={"email": "bo@example.com", "password": PW}).status_code == 200
