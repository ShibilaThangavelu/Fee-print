// Small fetch wrapper around the FeePrint mock API. In production this
// same shape would point at API Gateway instead of localhost.
import type {
  CurrenciesResponse,
  MeResponse,
  MidRateResponse,
  PaymentMethod,
  QuoteDetailResponse,
  QuotesResponse,
  SignInFields,
  SignUpFields,
  UserResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    // Send the httpOnly session cookie the backend sets on sign-in.
    credentials: 'include',
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body: { detail?: string } = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore - not JSON
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

interface QuoteParams {
  amount: string | number;
  to: string;
  method?: PaymentMethod | string;
}

export function getQuotes({
  amount,
  to,
  from = 'AUD',
  method = 'bank_transfer',
}: QuoteParams & { from?: string }): Promise<QuotesResponse> {
  const params = new URLSearchParams({ amount: String(amount), to, from, method });
  return request<QuotesResponse>(`/api/quotes?${params.toString()}`);
}

export function getQuoteDetail(
  providerId: string,
  { amount, to, method = 'bank_transfer' }: QuoteParams,
): Promise<QuoteDetailResponse> {
  const params = new URLSearchParams({ amount: String(amount), to, method });
  return request<QuoteDetailResponse>(
    `/api/quotes/${encodeURIComponent(providerId)}?${params.toString()}`,
  );
}

export function getMidRate(to: string): Promise<MidRateResponse> {
  return request<MidRateResponse>(`/api/rate?to=${encodeURIComponent(to)}`);
}

export function getCurrencies(): Promise<CurrenciesResponse> {
  return request<CurrenciesResponse>('/api/currencies');
}

// ---- Accounts ---------------------------------------------------------

function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
}

export const authApi = {
  config: () => request<{ google_enabled: boolean }>('/api/auth/config'),
  me: () => request<MeResponse>('/api/auth/me'),
  signUp: ({ name, email, password }: SignUpFields) =>
    postJson<UserResponse>('/api/auth/signup', { name, email, password }),
  signIn: ({ email, password }: SignInFields) =>
    postJson<UserResponse>('/api/auth/signin', { email, password }),
  google: (credential: string) => postJson<UserResponse>('/api/auth/google', { credential }),
  signOut: () => postJson<{ ok: boolean }>('/api/auth/signout'),
};
