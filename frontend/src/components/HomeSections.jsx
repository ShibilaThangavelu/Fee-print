// Landing-page sections shown under the search hero on the home page.
import { useState } from 'react';
import { money } from '../lib/format';
import './home.css';

/* ------------------------------------------------------------------ the $0 trap demo */

// Example numbers only (not real providers) to show how a margin hidden in the rate works.
const ZERO_FEE = { name: 'Provider A', ad: '$0 fee', fee: 0, markup: 0.02 };
const FLAT_FEE = { name: 'Provider B', ad: 'A$4.99 fee', fee: 4.99, markup: 0.003 };
const AMOUNTS = [200, 1000, 2500, 5000];

function work(p, amount, mid) {
  const rate = mid * (1 - p.markup);
  const receives = (amount - p.fee) * rate;
  const feeLoss = (p.fee * rate) / mid;                 // AUD
  const markupLoss = (amount * (mid - rate)) / mid;     // AUD
  return { receives, feeLoss, markupLoss, total: feeLoss + markupLoss };
}

export function TrapDemo({ midRate }) {
  const mid = midRate?.rate || 66.77;
  const [amount, setAmount] = useState(1000);
  const [revealed, setRevealed] = useState(false);
  const ideal = amount * mid;
  const a = work(ZERO_FEE, amount, mid);
  const b = work(FLAT_FEE, amount, mid);
  const winner = a.total > b.total ? FLAT_FEE : ZERO_FEE;
  const gapAud = Math.abs(a.total - b.total);

  // Zoom: the track shows only the last 10% of the ideal amount, so a 2% gap is visible.
  const ZOOM_FROM = 0.9;
  const recvPct = (inr) => `${Math.max(0, Math.min(100, ((inr / ideal - ZOOM_FROM) / (1 - ZOOM_FROM)) * 100))}%`;
  const lossPct = (inr) => `${Math.max(0, Math.min(100, (inr / ideal / (1 - ZOOM_FROM)) * 100))}%`;

  function Bar({ p, w }) {
    const feeInr = w.feeLoss * mid;
    const markInr = w.markupLoss * mid;
    return (
      <div className="trap-row">
        <div className="trap-row-head">
          <strong>{p.name}</strong>
          <span className="trap-ad">Advertises: {p.ad}</span>
        </div>
        <div className="trap-track" role="img"
          aria-label={`${p.name} delivers ${money(w.receives, 0)} rupees out of an ideal ${money(ideal, 0)}`}>
          <span className="seg seg-recv" style={{ width: recvPct(w.receives) }} />
          <span className={`seg ${revealed ? 'seg-hidden' : 'seg-recv'}`} style={{ width: lossPct(markInr) }} />
          <span className="seg seg-fee" style={{ width: lossPct(feeInr) }} />
        </div>
        <div className="trap-row-foot">
          <span>Arrives: <b>₹{money(w.receives, 0)}</b></span>
          <span className={revealed ? 'trap-cost shown' : 'trap-cost'}>
            Real cost: <b>A${money(w.total)}</b>
          </span>
        </div>
      </div>
    );
  }

  return (
    <section className="trap" aria-labelledby="trap-title">
      <div className="container trap-inner">
        <div className="trap-copy">
          <h2 id="trap-title">Which one costs more?</h2>
          <p>Same amount. One says $0 fee. Drag, then reveal.</p>

          <label htmlFor="trap-amount" className="trap-label">You send</label>
          <div className="trap-amount">A${money(amount, 0)}</div>
          <input id="trap-amount" type="range" min="200" max="5000" step="100"
            value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
          <div className="trap-chips">
            {AMOUNTS.map((v) => (
              <button key={v} type="button" className={amount === v ? 'chip on' : 'chip'}
                onClick={() => setAmount(v)}>A${money(v, 0)}</button>
            ))}
          </div>

          <button type="button" className="trap-reveal" aria-pressed={revealed}
            onClick={() => setRevealed((r) => !r)}>
            {revealed ? 'Hide it again' : 'Reveal the real cost'}
          </button>
        </div>

        <div className="trap-board">
          <Bar p={ZERO_FEE} w={a} />
          <Bar p={FLAT_FEE} w={b} />
          <div className="trap-legend">
            <span><i className="dot dot-recv" /> What arrives</span>
            <span><i className="dot dot-fee" /> Fee</span>
            <span><i className="dot dot-hidden" /> Cost hidden in the exchange rate</span>
          </div>
          <p className="trap-verdict" aria-live="polite">
            {revealed
              ? `${winner.name} sends ₹${money(gapAud * mid, 0)} more (A$${money(gapAud)}).`
              : 'Both look cheap. Now check the rate.'}
          </p>
          <p className="trap-note">Example numbers, not real providers. Bars zoom in on the last 10%.</p>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ icons */

const Svg = ({ children }) => (
  <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="currentColor"
    strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);
const IconTag = () => <Svg><path d="M6 24V8a2 2 0 0 1 2-2h16l18 18-18 18z" /><circle cx="16" cy="16" r="3" /></Svg>;
const IconSwap = () => <Svg><path d="M8 18h30m0 0-7-7m7 7-7 7M40 32H10m0 0 7-7m-7 7 7 7" /></Svg>;
const IconReceipt = () => <Svg><path d="M10 6h28v36l-5-3-4 3-5-3-5 3-4-3-5 3zM17 16h14M17 24h14M17 32h8" /></Svg>;
const IconPage = () => <Svg><rect x="6" y="8" width="36" height="32" rx="4" /><path d="M6 17h36M12 12.5h.01M17 12.5h.01" /><path d="M14 26h20M14 33h12" /></Svg>;
const IconPrint = () => <Svg><path d="M14 40c0-8 0-14 0-18a10 10 0 0 1 20 0c0 6 0 12-2 18M20 40c1-6 1-12 1-18a3 3 0 0 1 6 0c0 6-1 12-3 17M9 30c1-4 1-8 1-12" /></Svg>;
const IconCalc = () => <Svg><rect x="9" y="5" width="30" height="38" rx="4" /><path d="M15 13h18M16 22h.01M24 22h.01M32 22h.01M16 30h.01M24 30h.01M32 30h.01M16 37h.01M24 37h.01M32 37h.01" /></Svg>;
const IconLock = () => <Svg><rect x="9" y="21" width="30" height="21" rx="4" /><path d="M16 21v-6a8 8 0 0 1 16 0v6M24 30v5" /></Svg>;
const IconNoCard = () => <Svg><rect x="5" y="11" width="38" height="26" rx="4" /><path d="M5 20h38M8 42 40 6" /></Svg>;
const IconScale = () => <Svg><path d="M24 6v36M12 42h24M10 14h28M10 14l-6 14a6 6 0 0 0 12 0zM38 14l-6 14a6 6 0 0 0 12 0z" /></Svg>;
const IconEye = () => <Svg><path d="M3 24s7-14 21-14 21 14 21 14-7 14-21 14S3 24 3 24z" /><circle cx="24" cy="24" r="6" /></Svg>;

/* ------------------------------------------------------------------ why this exists */

export function WhySection() {
  return (
    <section className="home-section container" aria-labelledby="why-title">
      <h2 id="why-title" className="home-h2">Two costs. One you can&apos;t see.</h2>
      <div className="why-sum">
        <div className="why-tile"><IconTag /><b>Fee</b><span>Shown</span></div>
        <span className="why-op">+</span>
        <div className="why-tile why-hidden"><IconSwap /><b>Rate gap</b><span>Hidden</span></div>
        <span className="why-op">=</span>
        <div className="why-tile why-total"><IconReceipt /><b>Real cost</b><span>FeePrint shows this</span></div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ how it works */

const STEPS = [
  { icon: <IconPage />, title: 'Read', line: 'We read each provider\u2019s public page.',
    under: 'Playwright loads it. Beautiful Soup reads it. Gemini only helps with messy text.' },
  { icon: <IconPrint />, title: 'Save proof', line: 'Every price keeps a fingerprint of its page.',
    under: 'SHA-256 hash of the saved page. A number is rejected unless it appears in the text.' },
  { icon: <IconCalc />, title: 'Calculate', line: 'Same formulas for everyone. No AI maths.',
    formula: ['Gets = (amount \u2212 fee) \u00d7 rate', 'Cost = amount \u00d7 mid \u2212 gets'],
    under: 'Plain Python in calc.py.' },
  { icon: <IconEye />, title: 'Show', line: 'Open any result to see the working and the source.',
    under: 'FastAPI + SQLite. Prices over 24 hours old are hidden.' },
];

export function HowSection() {
  const [i, setI] = useState(0);
  const s = STEPS[i];
  return (
    <section id="how-we-calculate" className="home-section container" aria-labelledby="how-title">
      <h2 id="how-title" className="home-h2">How it works</h2>
      <div className="how-row" role="tablist" aria-label="Steps">
        {STEPS.map((st, idx) => (
          <button key={st.title} role="tab" type="button" aria-selected={i === idx}
            aria-controls="how-panel" id={`how-tab-${idx}`}
            className={i === idx ? 'how-card on' : 'how-card'} onClick={() => setI(idx)}>
            {st.icon}
            <span className="how-title">{st.title}</span>
            <span className="how-step">{idx + 1}</span>
          </button>
        ))}
      </div>
      <div className="how-panel" role="tabpanel" id="how-panel" aria-labelledby={`how-tab-${i}`}>
        <p className="how-line">{s.line}</p>
        {s.formula && (
          <div className="how-formula">{s.formula.map((f) => <code key={f}>{f}</code>)}</div>
        )}
        <p className="how-under">{s.under}</p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ how it differs */

const ROWS = [
  ['Cost shown', 'The fee, or a headline rate', 'Fee + rate gap = real cost'],
  ['Benchmark', 'None', 'Daily mid-market rate'],
  ['Proof', 'Take their word', 'Link and page fingerprint'],
  ['How fresh', 'Date unclear', 'Dated. Hidden after 24 hours'],
  ['Introductory deals', 'Mixed in with normal prices', 'Labelled \u201cNew-customer offer\u201d'],
];

const Tick = () => (
  <svg className="diff-tick" viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor"
    strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 10.5l4 4 8-9" /></svg>
);

export function DifferSection() {
  return (
    <section className="home-section container" aria-labelledby="diff-title">
      <h2 id="diff-title" className="home-h2">FeePrint vs a typical price list</h2>
      <div className="diff" role="table" aria-label="A typical price list compared with FeePrint">
        <div className="diff-row diff-head" role="row">
          <span role="columnheader" />
          <span role="columnheader">Typical price list</span>
          <span role="columnheader" className="diff-us">FeePrint</span>
        </div>
        {ROWS.map(([what, them, us]) => (
          <div className="diff-row" role="row" key={what}>
            <span role="rowheader" className="diff-what">{what}</span>
            <span role="cell" className="diff-them" data-label="Typical">{them}</span>
            <span role="cell" className="diff-us" data-label="FeePrint"><Tick />{us}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ privacy & safety */

const SAFE = [
  { icon: <IconLock />, title: 'Passwords are hashed', text: 'Stored scrambled. Never in plain text.' },
  { icon: <IconNoCard />, title: 'No bank or card details', text: 'We never ask for them and never move your money.' },
  { icon: <IconPage />, title: 'Public prices only', text: 'We read what providers publish. No logins.' },
  { icon: <IconScale />, title: 'Information, not advice', text: 'Estimates only. Confirm with the provider.' },
];

export function SafetySection() {
  return (
    <section id="privacy" className="home-section container" aria-labelledby="safe-title">
      <h2 id="safe-title" className="home-h2">Your privacy and safety</h2>
      <div className="safe-grid">
        {SAFE.map((x) => (
          <article className="safe" key={x.title}>
            {x.icon}
            <h3>{x.title}</h3>
            <p>{x.text}</p>
          </article>
        ))}
      </div>
      <p className="safe-note">
        An account stores only your name and email. FeePrint is a student project. It is not a
        bank or a licensed financial service, and we don&apos;t claim any financial-services
        certification.
      </p>
    </section>
  );
}

/* ------------------------------------------------------------------ providers + closing */

export function ProvidersSection() {
  return (
    <section id="providers-covered" className="home-section container" aria-labelledby="prov-title">
      <h2 id="prov-title" className="home-h2">Providers covered</h2>
      <div className="prov-row">
        <span className="prov-pill live"><i /> Wise</span>
        <span className="prov-pill live"><i /> Remitly</span>
        <span className="prov-pill soon">More soon</span>
      </div>
      <p className="prov-note">Public pages only. We say who we are.</p>
    </section>
  );
}

export function ClosingCta() {
  function toTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => document.getElementById('amount')?.focus(), 400);
  }
  return (
    <section className="closing">
      <div className="container closing-inner">
        <h2>Check your next transfer.</h2>
        <button type="button" className="closing-btn" onClick={toTop}>Compare providers</button>
      </div>
    </section>
  );
}
