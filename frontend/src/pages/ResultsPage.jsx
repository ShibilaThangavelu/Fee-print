import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { track } from '../lib/analytics';
import ProviderCard from '../components/ProviderCard';
import { getQuotes } from '../lib/api';
import { money, shortTime } from '../lib/format';
import './results-page.css';

const SORTS = [
  { key: 'received', label: 'Most received' },
  { key: 'fastest', label: 'Fastest' },
  { key: 'cost', label: 'Lowest total cost' },
];

function sortProviders(providers, sortKey) {
  const copy = [...providers];
  if (sortKey === 'fastest') {
    copy.sort((a, b) => a.speed_minutes_max - b.speed_minutes_max);
  } else if (sortKey === 'cost') {
    copy.sort((a, b) => a.total_cost - b.total_cost);
  } else {
    copy.sort((a, b) => b.recipient_gets - a.recipient_gets);
  }
  return copy;
}

export default function ResultsPage() {
  const [searchParams] = useSearchParams();
  const amount = searchParams.get('amount') || '1000';
  const to = searchParams.get('to') || 'INR';
  const method = searchParams.get('method') || 'bank_transfer';

  const [sortKey, setSortKey] = useState('received');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    getQuotes({ amount, to, method })
      .then((res) => {
        if (cancelled) return;
        setData(res);
        track('results_viewed', { to, provider_count: res.providers.length, source: res.source });
      })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [amount, to, method]);

  const sorted = useMemo(
    () => (data ? sortProviders(data.providers, sortKey) : []),
    [data, sortKey],
  );

  const editSearchHref = `/?amount=${encodeURIComponent(amount)}&to=${encodeURIComponent(to)}`;

  return (
    <div className="fp-page">
      <Header mobileAction={{ label: 'Edit search', to: editSearchHref }} />
      <main className="results-main container">
        <div className="results-heading">
          <div>
            <h1>AUD {money(Number(amount), 0)} to {data?.corridor?.to_country || '…'}</h1>
            <p className="results-sub">
              Paying by {method === 'debit_card' ? 'debit card' : 'bank transfer'}
              {data ? ` · ${sorted.length} providers compared` : ''} ·{' '}
              <Link to={editSearchHref}>Edit search</Link>
            </p>
          </div>
          {data && (
            <div className="mid-rate-card">
              <span>Daily reference rate (ECB mid-market)</span>
              <span className="mono">1 AUD = {money(data.mid_market_rate.rate)} {to}</span>
              <span>
                Ideal result: {money(data.ideal_amount)} {to} · as of {shortTime(data.mid_market_rate.as_of)}
              </span>
            </div>
          )}
        </div>

        {data?.source === 'mock' && (
          <p className="sample-notice">
            Sample data: FeePrint hasn&apos;t collected real prices for this corridor yet.
          </p>
        )}

        {error && (
          <p className="results-error">
            Couldn&apos;t reach the FeePrint API ({error}). Is the backend running on port 8000?
          </p>
        )}

        {!error && (
          <>
            <div role="group" aria-label="Sort results" className="sort-group">
              {SORTS.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  aria-pressed={sortKey === s.key}
                  className={`sort-btn${sortKey === s.key ? ' active' : ''}`}
                  onClick={() => setSortKey(s.key)}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {!data && <p className="results-loading">Comparing providers…</p>}

            {data && (
              <>
                {sorted.length === 0 && (
                  <div className="empty-state">
                    <h2>No current prices for this corridor</h2>
                    <p>
                      We hide prices older than 24 hours rather than show you something out of date.
                      Try again later or <Link to="/">search another amount</Link>.
                    </p>
                  </div>
                )}

                <div className="results-list">
                  {sorted.map((p) => (
                    <ProviderCard
                      key={p.id}
                      provider={p}
                      detailHref={`/detail/${p.id}?amount=${amount}&to=${to}&method=${method}`}
                    />
                  ))}
                </div>

                {data.hidden_count > 0 && (
                  <div className="hidden-note">
                    <span>
                      {data.hidden_count} provider{data.hidden_count > 1 ? 's' : ''} hidden:{' '}
                      {data.hidden_reason}.
                    </span>
                    <a href="#why-we-hide-old-prices">Why we hide old prices</a>
                  </div>
                )}

                {sorted.some((p) => p.beats_reference) && (
                  <p className="results-disclaimer">
                    *No markup shown: the provider&apos;s rate is at or above the daily ECB reference
                    rate (which is published once a day, so live rates can differ slightly).
                  </p>
                )}
                <p className="results-disclaimer">
                  Estimates based on each provider&apos;s publicly displayed prices at the time
                  shown. General information, not financial advice. Confirm the final amount with
                  the provider before you send.
                  {data.source === 'mock' && ' Provider names and prices here are placeholders.'}
                </p>
              </>
            )}
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
