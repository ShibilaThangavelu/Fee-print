import { Link } from 'react-router-dom';
import { money } from '../lib/format';
import './provider-card.css';

const BADGE_TEXT = {
  most_received: 'Most received',
  zero_fee_notice: 'Advertises $0 fee',
  stale_warning: 'May be out of date',
};

const BADGE_CLASS = {
  most_received: 'badge-best',
  zero_fee_notice: 'badge-neutral',
  stale_warning: 'badge-stale',
};

export default function ProviderCard({ provider, detailHref }) {
  const isBest = provider.badge === 'most_received';
  const isStale = provider.status === 'stale';

  return (
    <article className={`provider-card${isBest ? ' is-best' : ''}`}>
      <div className="pc-name">
        <span className="pc-name-text">{provider.name}</span>
        {provider.is_promo && <span className="pc-badge badge-neutral">New-customer offer</span>}
        {provider.badge && (
          <span className={`pc-badge ${BADGE_CLASS[provider.badge]}`}>
            {BADGE_TEXT[provider.badge]}
          </span>
        )}
      </div>

      <span className={`pc-amount${isBest ? ' pc-amount-best' : ''}`}>
        {money(provider.recipient_gets)} {provider.recipient_currency}
      </span>

      <div className="pc-metric pc-fee">
        <span className="pc-metric-label">Fee</span>
        <span className="pc-metric-value">{money(provider.fee)} {provider.fee_currency}</span>
      </div>
      <div className="pc-metric pc-markup">
        <span className="pc-metric-label">FX markup</span>
        <span className="pc-metric-value">
          {provider.beats_reference ? 'None*' : `${provider.fx_markup_pct.toFixed(2)}%`}
        </span>
      </div>
      <div className="pc-metric pc-total">
        <span className="pc-metric-label">Total cost</span>
        <span className="pc-metric-value">
          {provider.beats_reference
            ? 'None*'
            : `${money(provider.total_cost)} ${provider.recipient_currency} (${provider.total_cost_pct.toFixed(2)}%)`}
        </span>
      </div>
      <div className="pc-metric pc-speed">
        <span className="pc-metric-label">Speed</span>
        <span className="pc-metric-value pc-speed-value">{provider.speed_label}</span>
      </div>

      <div className="pc-actions">
        <Link to={detailHref}>See calculation</Link>
        <Link to={detailHref}>Evidence</Link>
      </div>

      <p className={`pc-footer${isStale ? ' is-stale' : ''}`}>
        <span>{provider.checked_label} &middot; {provider.note}</span>
        <Link to={detailHref} className="pc-footer-link">Calculation and evidence</Link>
      </p>
    </article>
  );
}
