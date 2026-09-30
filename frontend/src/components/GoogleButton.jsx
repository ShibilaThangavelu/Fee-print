// "Continue with Google" using Google Identity Services (GIS).
//
// Flow: Google's script draws the official button. When the user picks
// an account, Google calls onCredential() with an ID token (a signed
// JWT). We send that token to our backend, which verifies it with
// Google's public keys before creating/signing in the account.
import { useEffect, useRef, useState } from 'react';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GIS_SRC = 'https://accounts.google.com/gsi/client';

let gisPromise;
function loadGis() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!gisPromise) {
    gisPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = GIS_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        gisPromise = null;
        reject(new Error('Could not load Google sign-in.'));
      };
      document.head.appendChild(script);
    });
  }
  return gisPromise;
}

export default function GoogleButton({ text = 'continue_with', onCredential, onError }) {
  const wrapRef = useRef(null);
  const btnRef = useRef(null);
  const [failed, setFailed] = useState(false);

  // Keep the latest callbacks without re-rendering Google's button.
  const handlers = useRef({ onCredential, onError });
  useEffect(() => {
    handlers.current = { onCredential, onError };
  });

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    loadGis()
      .then(() => {
        if (cancelled || !btnRef.current) return;
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (response) => handlers.current.onCredential?.(response.credential),
          ux_mode: 'popup',
        });
        const width = Math.min(400, Math.max(200, wrapRef.current?.offsetWidth || 400));
        window.google.accounts.id.renderButton(btnRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          shape: 'rectangular',
          text,
          logo_alignment: 'center',
          width,
        });
      })
      .catch((err) => {
        if (!cancelled) {
          setFailed(true);
          handlers.current.onError?.(err.message);
        }
      });
    return () => { cancelled = true; };
  }, [text]);

  if (!CLIENT_ID) {
    return (
      <div className="google-missing">
        <button type="button" className="google-fallback" disabled>
          <GoogleG /> Continue with Google
        </button>
      </div>
    );
  }

  return (
    <div ref={wrapRef} className="google-btn-wrap">
      <div ref={btnRef} />
      {failed && <p className="google-missing">Couldn&apos;t reach Google. Check your connection.</p>}
    </div>
  );
}

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}
