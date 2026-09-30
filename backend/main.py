"""
FeePrint mock API.

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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import auth
import data

app = FastAPI(title="FeePrint mock API", version="0.1.0")

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
app.include_router(auth.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/currencies")
def currencies():
    return {"currencies": data.get_supported_currencies()}


@app.get("/api/quotes")
def quotes(
    amount: float = Query(1000, gt=0, le=1_000_000),
    to: str = Query("INR", min_length=3, max_length=3),
    from_currency: str = Query("AUD", alias="from", min_length=3, max_length=3),
    method: str = Query("bank_transfer"),
):
    if from_currency.upper() != "AUD":
        raise HTTPException(status_code=400, detail="Only AUD sends are supported in this mock.")
    if to.upper() not in data.MID_MARKET_RATES:
        raise HTTPException(status_code=400, detail=f"Unsupported destination currency: {to}")
    return data.build_quotes(amount=amount, to_currency=to, method=method)


@app.get("/api/quotes/{provider_id}")
def quote_detail(
    provider_id: str,
    amount: float = Query(1000, gt=0, le=1_000_000),
    to: str = Query("INR", min_length=3, max_length=3),
    method: str = Query("bank_transfer"),
):
    full, provider = data.get_provider_quote(provider_id, amount=amount, to_currency=to, method=method)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    return {
        "corridor": full["corridor"],
        "mid_market_rate": full["mid_market_rate"],
        "ideal_amount": full["ideal_amount"],
        "provider": provider,
    }
