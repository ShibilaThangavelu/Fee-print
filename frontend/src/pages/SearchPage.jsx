import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { getMidRate } from '../lib/api';
import { money, shortTime } from '../lib/format';
import './search-page.css';

const DESTINATIONS = [
  { code: 'INR', label: 'India · Indian rupee (INR)' },
  { code: 'PHP', label: 'Philippines · Philippine peso (PHP)' },
  { code: 'CNY', label: 'China · Chinese yuan (CNY)' },
  { code: 'VND', label: 'Vietnam · Vietnamese dong (VND)' },
  { code: 'GBP', label: 'United Kingdom · Pound sterling (GBP)' },
];

export default function SearchPage() {
  const navigate = useNavigate();
  const [amount, setAmount] = useState('1,000.00');
  const [dest, setDest] = useState('INR');
  const [method, setMethod] = useState('bank_transfer');
  const [midRate, setMidRate] = useState(null);

  useEffect(() => {
    let cancelled = false;
    // A cheap call just to surface the current mid-market rate live,
    // the same way the real search Lambda would look it up before the
    // user even hits "Compare".
    getMidRate(dest)
      .then((data) => {
        if (!cancelled) setMidRate(data.mid_market_rate);
      })
      .catch(() => {
        if (!cancelled) setMidRate(null);
      });
    return () => { cancelled = true; };
  }, [dest]);

  function handleSubmit(e) {
    e.preventDefault();
    const numeric = parseFloat(amount.replace(/,/g, '')) || 1000;
    const params = new URLSearchParams({
      amount: numeric,
      to: dest,
      method,
    });
    navigate(`/results?${params.toString()}`);
  }

  return (
    <div className="fp-page">
      <Header />
      <main className="search-main container">
        <section className="search-pitch">
          <p className="eyebrow">Money transfer comparison</p>
          <h1>See what your transfer really costs.</h1>
          <p className="lede">
            &ldquo;$0 fee&rdquo; often hides a worse exchange rate. We add the fee and the
            exchange-rate markup, show how much actually arrives, and link to the page every
            number came from.
          </p>
          <ul className="checklist">
            <li><Check /> Fee and exchange-rate markup in one total</li>
            <li><Check /> Evidence snapshot behind every price</li>
            <li><Check /> Prices checked every hour</li>
          </ul>
        </section>

        <form className="search-form" onSubmit={handleSubmit} aria-label="Compare transfers">
          <h2>Compare providers</h2>

          <div className="field">
            <label htmlFor="amount">You send</label>
            <div className="amount-input">
              <input
                id="amount"
                type="text"
                inputMode="decimal"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <div className="amount-suffix">AUD</div>
            </div>
          </div>

          <div className="field">
            <label htmlFor="dest">Recipient gets money in</label>
            <select id="dest" value={dest} onChange={(e) => setDest(e.target.value)}>
              {DESTINATIONS.map((d) => (
                <option key={d.code} value={d.code}>{d.label}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="pay">You pay by</label>
            <select id="pay" value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="bank_transfer">Bank transfer</option>
              <option value="debit_card">Debit card</option>
            </select>
          </div>

          <div className="mid-rate-row">
            <span>Mid-market rate</span>
            <span className="mono">
              {midRate
                ? `1 AUD = ${money(midRate.rate)} ${dest} · ${shortTime(midRate.as_of)}`
                : 'Looking up…'}
            </span>
          </div>

          <button type="submit" className="compare-btn">Compare providers</button>
          <p className="fine-print">
            Estimates from publicly displayed information. No account needed and we don&apos;t
            store what you search.
          </p>
        </form>
      </main>
    </div>
  );
}

function Check() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10.5l4 4 8-9" stroke="#0B6B4E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
