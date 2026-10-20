/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_POSTHOG_KEY?: string;
  readonly VITE_POSTHOG_HOST?: string;
  readonly VITE_GOOGLE_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Minimal typing for the parts of Google Identity Services we use.
interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleButtonOptions {
  type?: 'standard' | 'icon';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  logo_alignment?: 'left' | 'center';
  width?: number;
}

interface Window {
  google?: {
    accounts?: {
      id?: {
        initialize(config: {
          client_id: string;
          callback: (response: GoogleCredentialResponse) => void;
          ux_mode?: 'popup' | 'redirect';
        }): void;
        renderButton(parent: HTMLElement, options: GoogleButtonOptions): void;
        disableAutoSelect?: () => void;
      };
    };
  };
}
