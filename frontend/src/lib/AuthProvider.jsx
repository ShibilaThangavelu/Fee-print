// Holds "who is signed in" for the whole app. Any component can call
// useAuth() (from auth-context.js) to read the user or sign in / out.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { authApi } from './api';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, ask the backend whether our session cookie is valid.
  useEffect(() => {
    authApi
      .me()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const signUp = useCallback(async (fields) => {
    const { user } = await authApi.signUp(fields);
    setUser(user);
    return user;
  }, []);

  const signIn = useCallback(async (fields) => {
    const { user } = await authApi.signIn(fields);
    setUser(user);
    return user;
  }, []);

  const signInWithGoogle = useCallback(async (credential) => {
    const { user } = await authApi.google(credential);
    setUser(user);
    return user;
  }, []);

  const signOut = useCallback(async () => {
    await authApi.signOut();
    setUser(null);
    // Stop Google auto-selecting this account next time.
    window.google?.accounts?.id?.disableAutoSelect?.();
  }, []);

  const value = useMemo(
    () => ({ user, loading, signUp, signIn, signInWithGoogle, signOut }),
    [user, loading, signUp, signIn, signInWithGoogle, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

