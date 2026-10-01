import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth-context';
import './header.css';

export default function Header({ mobileAction }) {
  const { user, loading, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const onAuthPage = location.pathname === '/signin' || location.pathname === '/signup';
  // Remember the current page so sign-in can bring the user back here.
  const here = { from: location.pathname + location.search };

  async function handleSignOut() {
    await signOut();
    navigate('/');
  }

  return (
    <header className="fp-header">
      <div className="fp-header-inner container">
        <Link to="/" className="fp-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <rect x="1" y="1" width="26" height="26" rx="7" stroke="#7A2E8E" strokeWidth="2" />
            <path d="M8 18l4-4 3 3 5-6" stroke="#7A2E8E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>FeePrint</span>
        </Link>
        <nav aria-label="Main" className="fp-nav">
          <Link to="/">Compare</Link>
          <Link to="/#how-we-calculate">How it works</Link>
          <Link to="/#providers-covered">Providers covered</Link>
        </nav>

        <div className="fp-right">
          {mobileAction && (
            <Link to={mobileAction.to} className="fp-mobile-action">
              {mobileAction.label}
            </Link>
          )}

          {!loading && !onAuthPage && (
            user ? (
              <div className="fp-account">
                <span className="fp-avatar" aria-hidden="true">
                  {user.name.charAt(0).toUpperCase()}
                </span>
                <span className="fp-user-name">{user.name}</span>
                <button type="button" className="fp-signout" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            ) : (
              <div className="fp-account">
                <Link to="/signin" state={here} className="fp-signin">Sign in</Link>
                <Link to="/signup" state={here} className="fp-signup">Sign up</Link>
              </div>
            )
          )}
        </div>
      </div>
    </header>
  );
}
