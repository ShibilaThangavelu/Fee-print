import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import Header from '../components/Header';
import { getQuoteDetail } from '../lib/api';
import { money, shortTime } from '../lib/format';
import './detail-page.css';

export default function DetailPage() {
  const { providerId } = useParams();
  const [searchParams] = useSearchParams();
  const amount = searchParams.get('amount') || '1000';
  const to = searchParams.get('to') || 'INR';
  const method = searchParams.get('method') || 'bank_transfer';

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const backHref = `/results?amount=${amount}&to=${to}&method=${method}`;

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    getQuoteDetail(providerId, { amount, to, method })
      .then((res) => { if (!cancelled) setData(res); })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [providerId, amount, to, method]);

  return (
    <div className="fp-page">
      <Header />
      <main className="detail-main container">
        <Link to={backHref} className="back-link">&larr; Back to results</Link>

        {error && (
          <p className="results-error">
            Couldn&apos;t load this provider ({error}).
          </p>
        )}

        {!error && !data && <p className="results-loading">Loading calculation…</p>}

        {data && (
          <>
            <div className="detail-heading">
              <div>
                <h1>{data.provider.name}: how we worked it out</h1>
                <p>
                  AUD {money(Number(amount), 0)} to {data.corridor.to_country} &middot;{' '}
                  {method === 'debit_card' ? 'debit card' : 'bank transfer'} &middot;{' '}
                  {data.provider.checked_label}
                </p>
              </div>
              <div className="detail-amount">
                <span>Recipient gets</span>
                <strong>{money(data.provider.recipient_gets)} {data.provider.recipient_currency}</strong>
              </div>
            </div>

            <div className="detail-columns">
              <section aria-labelledby="calc" className="calc-card">
                <h2 id="calc">The calculation</h2>
                <CalcRow n={1} label="You send" value={`AUD ${money(Number(amount))}`} />
                <CalcRow
                  n={2}
                  label={data.provider.fee_billing === 'added_on_top'
                    ? 'Fee, charged separately but counted here'
                    : 'Fee, deducted before conversion'}
                  value={`− AUD ${money(data.provider.fee)}`}
                />
                <CalcRow n={3} label="Amount converted" value={`AUD ${money(data.provider.amount_converted)}`} />
                <CalcRow n={4} label="Provider's rate" value={`× ${data.provider.provider_rate.toFixed(2)} ${to}`} />
                <CalcRow
                  n={5}
                  label="Recipient gets"
                  value={`${money(data.provider.recipient_gets)} ${to}`}
                  strong
                />
                <CalcRow
                  n={6}
                  label={`FX markup: (${data.mid_market_rate.rate.toFixed(2)} − ${data.provider.provider_rate.toFixed(2)}) ÷ ${data.mid_market_rate.rate.toFixed(2)}`}
                  value={`${data.provider.fx_markup_pct.toFixed(2)}%`}
                />
                <CalcRow
                  n={7}
                  label={`Total cost vs the ideal ${money(data.ideal_amount)} ${to}`}
                  value={`${money(data.provider.total_cost)} ${to} (${data.provider.total_cost_pct.toFixed(2)}%)`}
                  last
                />
                <p className="calc-footnote">
                  Mid-market rate {data.mid_market_rate.rate.toFixed(2)} from our licensed
                  reference source, as of {shortTime(data.mid_market_rate.as_of)}. Fee rules:{' '}
                  {data.provider.fee === 0
                    ? 'no fee for this transfer amount.'
                    : `flat AUD ${money(data.provider.fee)} for ${method === 'debit_card' ? 'debit card payments' : 'bank transfers'} up to AUD 5,000.`}
                </p>
              </section>

              <section aria-labelledby="evidence" className="evidence-card">
                <h2 id="evidence">Evidence</h2>
                <div
                  role="img"
                  aria-label={`Placeholder for the saved screenshot of ${data.provider.name}'s pricing page`}
                  className="evidence-shot"
                >
                  [Saved screenshot of the provider&apos;s pricing page]
                </div>
                <dl className="evidence-list">
                  <dt>Captured</dt>
                  <dd>{new Date(data.provider.evidence.captured_at).toLocaleString('en-AU')}</dd>
                  <dt>Source page</dt>
                  <dd><a href={data.provider.evidence.source_url}>[{data.provider.name} pricing page URL]</a></dd>
                  <dt>Integrity hash</dt>
                  <dd>SHA-256 {data.provider.evidence.sha256}</dd>
                  <dt>Kept unchanged until</dt>
                  <dd>{data.provider.evidence.retention_until}</dd>
                  <dt>Parser version</dt>
                  <dd>{data.provider.evidence.parser_version}</dd>
                </dl>
                <a href={data.provider.evidence.source_url} className="snapshot-btn">
                  Open full snapshot
                </a>
              </section>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function CalcRow({ n, label, value, strong, last }) {
  return (
    <div className={`calc-row${last ? ' calc-row-last' : ''}`}>
      <span className="calc-n">{n}</span>
      <span className={strong ? 'calc-label-strong' : undefined}>{label}</span>
      <span className={`calc-value${strong ? ' calc-value-strong' : ''}`}>{value}</span>
    </div>
  );
}
