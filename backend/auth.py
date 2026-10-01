"""
FeePrint accounts: email/password sign-up + sign-in, and "Continue with
Google".

How it fits together
--------------------
* Users live in a small SQLite database (feeprint.db, created on first
  run) - the project's suggested stack. In production this whole module
  is replaced by Amazon Cognito (user pool + Google as a federated
  identity provider), so no passwords are stored in our own tables.
* Passwords are never stored. We store a salted scrypt hash
  (hashlib.scrypt is in the Python standard library).
* After a successful sign-in the server sets an httpOnly cookie holding
  a signed JWT (the "session"). JavaScript in the page can't read it,
  which protects it from XSS; the browser just sends it back on each
  request.
* Google sign-in: the React page shows Google's button (Google Identity
  Services). When the user picks an account, Google hands the page an
  **ID token** (a JWT signed by Google). The page posts it to
  /api/auth/google, and here we verify Google's signature, the audience
  (our client ID) and the expiry before trusting anything in it.
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt  # PyJWT
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

DB_PATH = Path(os.getenv("FEEPRINT_DB", Path(__file__).with_name("feeprint.db")))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
SESSION_COOKIE = "fp_session"
SESSION_DAYS = 7
# Cookies must be Secure (HTTPS-only) in production; plain http://localhost
# needs it off.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

_secret = os.getenv("SESSION_SECRET")
if not _secret:
    # Fine for local dev: sessions just reset whenever the server restarts.
    _secret = secrets.token_hex(32)
    print("[auth] SESSION_SECRET not set - using a temporary one (sessions reset on restart).")
SESSION_SECRET = _secret

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------- database

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT NOT NULL UNIQUE,
                name          TEXT NOT NULL,
                password_hash TEXT,            -- NULL for Google-only accounts
                google_sub    TEXT UNIQUE,     -- Google's stable user id
                created_at    TEXT NOT NULL
            )
            """
        )


def _public(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "has_password": row["password_hash"] is not None,
        "google_linked": row["google_sub"] is not None,
    }


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


# ---------------------------------------------------------------- sessions

def _set_session(response: Response, user_id: int):
    token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        },
        SESSION_SECRET,
        algorithm="HS256",
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def current_user(request: Request):
    """Return the signed-in user's row, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        claims = jwt.decode(token, SESSION_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    with _db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (int(claims["sub"]),)).fetchone()


def require_user(request: Request):
    """FastAPI dependency: only signed-in users get through, everyone else gets 401."""
    row = current_user(request)
    if row is None:
        raise HTTPException(status_code=401, detail="Please sign in to compare providers.")
    return row


# ---------------------------------------------------------------- routes

class SignUpBody(BaseModel):
    name: str
    email: str
    password: str


class SignInBody(BaseModel):
    email: str
    password: str


class GoogleBody(BaseModel):
    credential: str  # the ID token Google gave the browser


@router.get("/config")
def auth_config():
    """Lets the frontend know whether Google sign-in is set up."""
    return {"google_enabled": bool(GOOGLE_CLIENT_ID)}


@router.post("/signup", status_code=201)
def signup(body: SignUpBody, response: Response):
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name:
        raise HTTPException(400, "Please enter your name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters.")

    with _db() as conn:
        existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            hint = " Try “Continue with Google”." if existing["password_hash"] is None else ""
            raise HTTPException(409, "An account with this email already exists." + hint)
        cur = conn.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email, name, hash_password(body.password), datetime.now(timezone.utc).isoformat()),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()

    _set_session(response, row["id"])
    return {"user": _public(row)}


@router.post("/signin")
def signin(body: SignInBody, response: Response):
    email = body.email.strip().lower()
    with _db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row and row["password_hash"] is None:
        raise HTTPException(400, "This account uses Google sign-in. Use “Continue with Google”.")
    # Same message for "no such user" and "wrong password" so the form
    # can't be used to discover which emails have accounts.
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    _set_session(response, row["id"])
    return {"user": _public(row)}


@router.post("/google")
def google_signin(body: GoogleBody, response: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google sign-in isn't configured on the server (GOOGLE_CLIENT_ID).")

    # Imported here so the rest of the app still runs if google-auth
    # isn't installed yet.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(401, "Google sign-in could not be verified. Please try again.")

    sub = claims["sub"]
    email = (claims.get("email") or "").lower()
    name = claims.get("name") or email.split("@")[0]
    if not email or not claims.get("email_verified"):
        raise HTTPException(400, "Your Google account's email isn't verified.")

    with _db() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
        if row is None:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is not None:
                # Same verified email as an existing password account:
                # link Google to it rather than making a duplicate.
                conn.execute("UPDATE users SET google_sub = ? WHERE id = ?", (sub, row["id"]))
            else:
                cur = conn.execute(
                    "INSERT INTO users (email, name, google_sub, created_at) VALUES (?, ?, ?, ?)",
                    (email, name, sub, datetime.now(timezone.utc).isoformat()),
                )
                row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

    _set_session(response, row["id"])
    return {"user": _public(row)}


@router.get("/me")
def me(request: Request):
    row = current_user(request)
    return {"user": _public(row) if row else None}


@router.post("/signout")
def signout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}
