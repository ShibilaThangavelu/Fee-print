"""
FeePrint API.

A tiny FastAPI server that stands in for the real API Gateway + Lambda
search endpoint described in the architecture. It serves the same
shape of response the production Lambda would return, so the React
frontend calls a real URL (http://localhost:8000/api/...) exactly as
it would in production - only the data source behind it is a Python
dict instead of DynamoDB.

Run with:
    uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env (GOOGLE_CLIENT_ID, SESSION_SECRET) before auth imports them

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import auth
import calc
import data
import db

app = FastAPI(title="FeePrint API", version="0.2.0")

# Local Vite dev server (and a couple of common alternates) need CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    # Needed so the browser sends/receives the session cookie on
    # cross-port requests (5173 -> 8000).
    allow_credentials=True,
)

auth.init_db()
db.init_db()  # providers, captures, extracted_quotes, reference_rates
app.include_router(auth.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/currencies")
def currencies():
    return {"currencies": data.get_supported_currencies()}


def _quotes(amount: float, to: str, method: str) -> dict:
    """Real quotes from the database when the scraper has collected some for this
    corridor; otherwise the prototype's sample data, labelled so the screens can say so."""
    to = to.upper()
    if to not in data.MID_MARKET_RATES:
        raise HTTPException(status_code=400, detail=f"Unsupported destination currency: {to}")

    rows = db.latest_quotes(to)
    mid = db.latest_mid_rate("AUD", to)
    if rows and mid:
        # Real data that has gone stale is NOT swapped for sample data: it is
        # hidden (24 h rule) and counted in hidden_count, so users never see made-up prices.
        result = calc.build_quotes(
            rows, mid, amount, to_country=data.MID_MARKET_RATES[to]["country"], method=method
        )
        result["source"] = "database"
        return result

    result = data.build_quotes(amount=amount, to_currency=to, method=method)
    result["source"] = "mock"
    return result


@app.get("/api/rate")
def public_rate(to: str = Query("INR", min_length=3, max_length=3)):
    """Public teaser for the search page: today's mid-market rate only, no provider data."""
    return {"mid_market_rate": _quotes(1000, to, "bank_transfer")["mid_market_rate"]}


@app.get("/api/quotes", dependencies=[Depends(auth.require_user)])
def quotes(
    amount: float = Query(1000, gt=0, le=1_000_000),
    to: str = Query("INR", min_length=3, max_length=3),
    from_currency: str = Query("AUD", alias="from", min_length=3, max_length=3),
    method: str = Query("bank_transfer"),
):
    if from_currency.upper() != "AUD":
        raise HTTPException(status_code=400, detail="Only AUD sends are supported for now.")
    return _quotes(amount, to, method)


@app.get("/api/quotes/{provider_id}", dependencies=[Depends(auth.require_user)])
def quote_detail(
    provider_id: str,
    amount: float = Query(1000, gt=0, le=1_000_000),
    to: str = Query("INR", min_length=3, max_length=3),
    method: str = Query("bank_transfer"),
):
    full = _quotes(amount, to, method)
    provider = next((p for p in full["providers"] if p["id"] == provider_id), None)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    return {
        "corridor": full["corridor"],
        "mid_market_rate": full["mid_market_rate"],
        "ideal_amount": full["ideal_amount"],
        "provider": provider,
        "source": full["source"],
    }
