// Shared layout for the Sign in and Sign up screens.
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import GoogleButton from '../components/GoogleButton';
import { useAuth } from '../lib/auth-context';
import './auth-page.css';

export default function AuthPage({ mode }) {
  const isSignUp = mode === 'signup';
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  // Send people back to where they were (e.g. a results page) after signing in.
  const from = location.state?.from || '/';
  const needsLogin = location.state?.reason === 'compare';

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function run(action) {
    setError('');
    setBusy(true);
    try {
      await action();
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    run(() => (isSignUp ? signUp({ name, email, password }) : signIn({ email, password })));
  }

  return (
    <div className="fp-page">
      <Header />
      <main className="auth-main container">
        <div className="auth-card">
          <h1>{isSignUp ? 'Create your account' : 'Welcome back'}</h1>
          <p className="auth-sub">
            {isSignUp
              ? 'Create a free account to compare providers.'
              : needsLogin
                ? 'Sign in to compare providers.'
                : 'Sign in to your FeePrint account.'}
          </p>

          <GoogleButton
            text={isSignUp ? 'signup_with' : 'continue_with'}
            onCredential={(credential) => run(() => signInWithGoogle(credential))}
            onError={setError}
          />

          <div className="auth-divider"><span>or</span></div>

          <form onSubmit={handleSubmit} noValidate>
            {isSignUp && (
              <div className="field">
                <label htmlFor="name">Name</label>
                <input
                  id="name"
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={isSignUp ? 8 : undefined}
                required
              />
              {isSignUp && <span className="hint">At least 8 characters.</span>}
            </div>

            {error && <p className="auth-error" role="alert">{error}</p>}

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="auth-switch">
            {isSignUp ? (
              <>Already have an account? <Link to="/signin" state={{ from, reason: location.state?.reason }}>Sign in</Link></>
            ) : (
              <>New to FeePrint? <Link to="/signup" state={{ from, reason: location.state?.reason }}>Create an account</Link></>
            )}
          </p>
        </div>
      </main>
    </div>
  );
}
