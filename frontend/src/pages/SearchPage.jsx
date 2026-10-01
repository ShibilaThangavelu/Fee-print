import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { track } from '../lib/analytics';
import { getMidRate } from '../lib/api';
import { money, shortTime } from '../lib/format';
import { ClosingCta, DifferSection, HowSection, ProvidersSection, SafetySection, TrapDemo, WhySection } from '../components/HomeSections';
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
  const { hash } = useLocation();
  const [amount, setAmount] = useState('1,000.00');
  const [dest, setDest] = useState('INR');
  const [amountError, setAmountError] = useState('');
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

  // Header links like /#how-we-calculate scroll to their section.
  useEffect(() => {
    if (!hash) return;
    const el = document.getElementById(hash.slice(1));
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, [hash]);

  function handleSubmit(e) {
    e.preventDefault();
    const numeric = Number(amount.replace(/,/g, ''));
    if (!Number.isFinite(numeric) || numeric < 50 || numeric > 100000) {
      setAmountError('Enter an amount between A$50 and A$100,000.');
      return;
    }
    setAmountError('');
    // Our prices are read from each provider's bank-transfer pricing.
    const params = new URLSearchParams({ amount: numeric, to: dest, method: 'bank_transfer' });
    track('search_submitted', { amount: numeric, to: dest });
    navigate(`/results?${params.toString()}`);
  }

  return (
    <div className="fp-page">
      <Header />
      <main className="hero">
        <div className="container hero-inner">
        <section className="hero-copy">
          <h1>&ldquo;$0 fee&rdquo; isn&rsquo;t the price.</h1>
          <p className="hero-lede">
            We compare what money-transfer providers really charge: the fee <em>plus</em> the
            exchange-rate gap that never shows up as a fee.
          </p>

          <div className="receipt" aria-label="Example: a $0 fee transfer of A$1,000 with a 2 percent rate gap">
            <p className="rc-cap">Example: A$1,000 to India with a &ldquo;$0 fee&rdquo; provider</p>
            <div className="rc rc-1"><span>Advertised fee</span><b>A$0</b></div>
            <div className="rc rc-2"><span>Hidden in the rate</span><b>&minus;A$20</b></div>
            <div className="rc rc-3"><span>Arrives</span><b>₹{money(1000 * (midRate?.rate || 66.77) * 0.98, 0)}</b></div>
            <p className="rc-note">You think you pay A$0. The rate gap quietly takes A$20.</p>
          </div>
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
                onChange={(e) => { setAmount(e.target.value); setAmountError(''); }}
                aria-invalid={!!amountError}
                aria-describedby={amountError ? 'amount-error' : undefined}
              />
              <div className="amount-suffix">AUD</div>
            </div>
            {amountError && <p id="amount-error" role="alert" className="field-error">{amountError}</p>}
          </div>

          <div className="field">
            <label htmlFor="dest">Recipient gets money in</label>
            <select id="dest" value={dest} onChange={(e) => setDest(e.target.value)}>
              {DESTINATIONS.map((d) => (
                <option key={d.code} value={d.code}>{d.label}</option>
              ))}
            </select>
          </div>


          <div className="mid-rate-row">
            <span>Daily reference rate (ECB)</span>
            <span className="mono">
              {midRate
                ? `1 AUD = ${money(midRate.rate)} ${dest} · ${shortTime(midRate.as_of)}`
                : 'Looking up…'}
            </span>
          </div>

          <button type="submit" className="compare-btn">Compare providers</button>
          <p className="fine-print">
            Estimates from publicly displayed information, for bank transfers. A free account is
            needed to compare providers.
          </p>
        </form>
        </div>
      </main>

      <TrapDemo midRate={midRate} />
      <WhySection />
      <HowSection />
      <DifferSection />
      <ProvidersSection />
      <SafetySection />
      <ClosingCta />
      <Footer />
    </div>
  );
}

