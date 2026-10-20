// Shapes of the data returned by the FeePrint API (backend/main.py, data.py, calc.py).

export type PaymentMethod = 'bank_transfer' | 'debit_card';
export type ProviderBadge = 'most_received' | 'zero_fee_notice' | 'stale_warning';
export type ProviderStatus = 'fresh' | 'stale' | string;
export type QuoteSource = 'database' | 'mock';

export interface Corridor {
  from_currency: string;
  to_currency: string;
  to_country: string;
  amount: number;
  method: string;
}

export interface MidMarketRate {
  rate: number;
  as_of: string;
  /** Present for real (database) quotes. */
  source?: string | null;
}

export interface CalcStep {
  step: string;
  formula: string;
  result: string;
}

export interface Evidence {
  source_url: string;
  captured_at: string;
  sha256: string;
  retention_until: string;
  parser_version: string;
  /** Only present for real, scraped quotes. */
  fee_text?: string;
  rate_text?: string;
}

export interface Provider {
  id: string;
  name: string;
  fee: number;
  fee_currency: string;
  fee_billing: 'deducted' | 'added_on_top' | string;
  fx_markup_pct: number;
  provider_rate: number;
  amount_converted: number;
  recipient_gets: number;
  recipient_currency: string;
  total_cost: number;
  total_cost_pct: number;
  speed_label: string;
  speed_minutes_max: number | null;
  checked_at: string;
  checked_minutes_ago: number;
  checked_label: string;
  status: ProviderStatus;
  note: string;
  badge: ProviderBadge | null;
  evidence: Evidence;
  /** Real (database) quotes only. */
  calc_steps?: CalcStep[];
  is_promo?: boolean;
  beats_reference?: boolean;
  fee_type?: string;
}

export interface QuotesResponse {
  corridor: Corridor;
  mid_market_rate: MidMarketRate;
  ideal_amount: number;
  providers: Provider[];
  hidden_count: number;
  hidden_reason: string | null;
  generated_at: string;
  source: QuoteSource;
}

export interface QuoteDetailResponse {
  corridor: Corridor;
  mid_market_rate: MidMarketRate;
  ideal_amount: number;
  provider: Provider;
  source: QuoteSource;
}

export interface MidRateResponse {
  mid_market_rate: MidMarketRate;
}

export interface Currency {
  code: string;
  country: string;
  name: string;
}

export interface CurrenciesResponse {
  currencies: Currency[];
}

export interface User {
  id: number;
  email: string;
  name: string;
  has_password: boolean;
  google_linked: boolean;
}

export interface UserResponse {
  user: User;
}

/** /api/auth/me returns user: null when signed out. */
export interface MeResponse {
  user: User | null;
}

export interface SignUpFields {
  name: string;
  email: string;
  password: string;
}

export interface SignInFields {
  email: string;
  password: string;
}
