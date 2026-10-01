// Wraps pages that need an account. Signed-out visitors are sent to the
// sign-in page and brought back here afterwards.
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth-context';

export default function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="container" style={{ padding: '3rem 0' }}>Loading…</p>;
  if (!user) {
    return (
      <Navigate
        to="/signin"
        replace
        state={{ from: location.pathname + location.search, reason: 'compare' }}
      />
    );
  }
  return children;
}
