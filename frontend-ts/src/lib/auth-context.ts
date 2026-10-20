// The auth context object and the useAuth() hook. The provider that
// fills it lives in AuthProvider.tsx.
import { createContext, useContext } from 'react';
import type { SignInFields, SignUpFields, User } from '../types';

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signUp: (fields: SignUpFields) => Promise<User>;
  signIn: (fields: SignInFields) => Promise<User>;
  signInWithGoogle: (credential: string) => Promise<User>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
