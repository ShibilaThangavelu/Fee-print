// Small fetch wrapper around the FeePrint mock API. In production this
// same shape would point at API Gateway instead of localhost.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    // Send the httpOnly session cookie the backend sets on sign-in.
    credentials: 'include',
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore - not JSON
    }
    throw new Error(detail);
  }
  return res.json();
}

export function getQuotes({ amount, to, from = 'AUD', method = 'bank_transfer' }) {
  const params = new URLSearchParams({ amount, to, from, method });
  return request(`/api/quotes?${params.toString()}`);
}

export function getQuoteDetail(providerId, { amount, to, method = 'bank_transfer' }) {
  const params = new URLSearchParams({ amount, to, method });
  return request(`/api/quotes/${encodeURIComponent(providerId)}?${params.toString()}`);
}

export function getCurrencies() {
  return request('/api/currencies');
}

// ---- Accounts ---------------------------------------------------------

function postJson(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
}

export const authApi = {
  config: () => request('/api/auth/config'),
  me: () => request('/api/auth/me'),
  signUp: ({ name, email, password }) => postJson('/api/auth/signup', { name, email, password }),
  signIn: ({ email, password }) => postJson('/api/auth/signin', { email, password }),
  google: (credential) => postJson('/api/auth/google', { credential }),
  signOut: () => postJson('/api/auth/signout'),
};
