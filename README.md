# FeePrint — prototype (React frontend + mock API backend)

A working, click-through build of the four FeePrint screens (search,
results, calculation/evidence, and a responsive mobile view), wired to
a small mock API instead of static/hardcoded data. It's built to be a
faithful, functioning version of the earlier front-end mock-up, and to
map cleanly onto the AWS architecture from the design doc:

| This prototype | Production equivalent |
|---|---|
| React (Vite) | React (Vite), served from S3 + CloudFront |
| FastAPI mock server | API Gateway (HTTP API) + Lambda |
| Python dict in `data.py` | DynamoDB `Quotes` / `ReferenceRates` tables |
| `GET /api/quotes` | The search Lambda's endpoint |

## What's included

```
feeprint-app/
├── backend/          FastAPI mock API
│   ├── main.py        routes: /api/quotes, /api/quotes/{id}, /api/currencies
│   ├── auth.py        accounts: sign up/in, Google, sessions (SQLite)
│   ├── data.py        mock provider data + the normalisation/calculation logic
│   └── requirements.txt
└── frontend/         React app (Vite)
    └── src/
        ├── pages/      SearchPage, ResultsPage, DetailPage, AuthPage (sign in/up)
        ├── components/ Header, ProviderCard, GoogleButton
        └── lib/        api.js (fetch wrapper), AuthProvider + auth-context (who's signed in), format.js
```

There is no separate "mobile screen" file — `ProviderCard` and the
page layouts are genuinely responsive (CSS Grid areas that
rearrange under 900px), so the same code renders the desktop table
layout and the one-column mobile layout from the mock-up.

## Why a real mock API instead of static JSON

The frontend calls `http://localhost:8000/api/quotes?...` over HTTP,
exactly like it would call API Gateway in production. That means:

- The normalisation/calculation logic (the actual hard part of
  FeePrint) lives in one place on the backend (`data.py`), not
  duplicated in frontend code.
- Sorting, badges ("Most received", "Advertises $0 fee", "May be out
  of date"), and the "hidden after 24h" rule are all computed
  server-side from raw per-provider inputs (fee, fx markup %, minutes
  since checked) — the same shape the extract/normalise/validate
  Lambda pipeline would produce.
- Swapping the mock backend for the real API Gateway URL later is a
  one-line env var change (`VITE_API_BASE`), not a rewrite.

## Running it locally

**Backend** (Python 3.10+):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional: add Google client ID + session secret
uvicorn main:app --reload --port 8000
```

**Frontend** (Node 20.19+ or 22+, which Vite 8 needs), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). Fill in
the search form and click "Compare providers" — everything after that
point is live data from the FastAPI server.

To point the frontend at a different backend URL, copy
`frontend/.env.example` to `frontend/.env` and edit `VITE_API_BASE`.

## Accounts: sign up / sign in / Google

Sign-in is optional. Comparing still works without an account.

- **Pages:** `/signup` and `/signin` (`frontend/src/pages/AuthPage.jsx`),
  plus Sign in / Sign up (or your name + Sign out) in the header.
- **Email + password:** stored in SQLite (`backend/feeprint.db`, created
  on first run). Passwords are saved only as salted scrypt hashes.
- **Session:** after sign-in the backend sets an httpOnly cookie
  (`fp_session`, a signed JWT, 7 days). The page's JavaScript can't read
  it, and `api.js` sends it with `credentials: 'include'`.
- **Google:** the page shows Google's own button (Google Identity
  Services). Google gives the browser an ID token, the browser posts it
  to `/api/auth/google`, and the backend verifies Google's signature and
  that the token was issued for *our* client ID before signing the user
  in. A Google account with the same verified email as an existing
  password account is linked to it instead of creating a duplicate.

| Endpoint | Does |
|---|---|
| `POST /api/auth/signup` | `{name, email, password}` → creates account, signs in |
| `POST /api/auth/signin` | `{email, password}` → signs in |
| `POST /api/auth/google` | `{credential}` (Google ID token) → signs in / creates account |
| `GET /api/auth/me` | who is signed in (`{"user": null}` if nobody) |
| `POST /api/auth/signout` | clears the session cookie |
| `GET /api/auth/config` | whether Google sign-in is configured |

### Setting up Google sign-in (one-off, about 5 minutes)

Email/password works with no setup. The Google button stays greyed out
until you do this:

1. Go to https://console.cloud.google.com/, create (or pick) a project.
2. **APIs & Services → OAuth consent screen**: choose *External*, fill in
   the app name and your email, and add yourself as a *test user*.
3. **APIs & Services → Credentials → Create credentials → OAuth client
   ID**, type **Web application**.
4. Under **Authorised JavaScript origins** add both
   `http://localhost:5173` **and** `http://localhost` (Google needs both
   for local dev). No redirect URI is needed.
5. Copy the client ID (ends in `.apps.googleusercontent.com`) into:
   - `backend/.env` as `GOOGLE_CLIENT_ID=...` (copy `backend/.env.example`)
   - `frontend/.env` as `VITE_GOOGLE_CLIENT_ID=...` (copy `frontend/.env.example`)
6. Put a random `SESSION_SECRET` in `backend/.env` too
   (`python3 -c "import secrets; print(secrets.token_hex(32))"`), so
   sessions survive a backend restart.
7. Restart both servers (Vite only reads `.env` at startup).

Open the app at **http://localhost:5173**, not `127.0.0.1`. The Google
origin and the session cookie are both set up for `localhost`.

### Production equivalent

In the AWS design this layer becomes **Amazon Cognito**: a user pool
with Google added as a federated identity provider, and API Gateway
using a Cognito JWT authoriser. We'd then stop storing passwords
ourselves. Because accounts mean personal data (email, name), add
privacy/retention/deletion handling at that point.

## API shape

```
GET /api/quotes?amount=1000&to=INR&from=AUD&method=bank_transfer
```
Returns the mid-market rate, the ideal (fee/markup-free) amount, and
the list of visible providers (each with fee, fx_markup_pct,
provider_rate, recipient_gets, total_cost, speed, checked_at/label,
status, badge, and an evidence block). Providers older than 24 hours
are excluded from the list but counted in `hidden_count`.

```
GET /api/quotes/{provider_id}?amount=1000&to=INR&method=bank_transfer
```
Same corridor context, plus the full detail for one provider — this
backs the calculation/evidence screen.

```
GET /api/currencies
```
The destination currencies the mock supports (INR, PHP, CNY, VND, GBP).

## What's mocked vs. real

- **Real:** the React UI, the routing between all four screens, the
  HTTP contract between frontend and backend, the normalisation math
  (fee + FX markup → total cost, badge assignment, stale/hidden
  rules).
- **Mocked:** the actual provider data (six fictional providers with
  fixed inputs in `data.py`), the "evidence" screenshot/hash/retention
  fields, and the mid-market rate (fixed per currency rather than
  pulled from a live feed).

## Suggested next steps

1. Swap `backend/data.py` for real reads from DynamoDB (or even just
   a seeded SQLite table, per the project's suggested stack) so the
   numbers change without redeploying code.
2. Add the extract/normalise pipeline that produces the rows this API
   reads, instead of hand-written mock inputs.
3. Add a loading skeleton and empty/error states are already present
   on the results and detail pages if you want a base to extend.
