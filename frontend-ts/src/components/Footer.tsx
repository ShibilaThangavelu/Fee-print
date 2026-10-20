import { Link } from 'react-router-dom';
import './home.css';

export default function Footer() {
  return (
    <footer className="fp-footer">
      <div className="container fp-footer-inner">
        <p>&copy; {new Date().getFullYear()} FeePrint. A student project.</p>
        <p>
          General information, not financial advice. Prices come from providers&apos; public pages.{' '}
          <Link to="/#privacy">Privacy and safety</Link>
        </p>
      </div>
    </footer>
  );
}
