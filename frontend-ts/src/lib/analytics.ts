// Sentry (errors) and PostHog (usage). Both are no-ops until their keys are in frontend/.env.local.
import * as Sentry from '@sentry/react';
import posthog from 'posthog-js';
import type { User } from '../types';

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';
let posthogOn = false;

export function initAnalytics(): void {
  if (SENTRY_DSN) {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: import.meta.env.MODE,
      tracesSampleRate: 0.1,
      // Default PII collection is off in this SDK version; no option needed.
    });
  }
  if (POSTHOG_KEY) {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      autocapture: true,
      person_profiles: 'identified_only',
      session_recording: { maskAllInputs: true },
    });
    posthogOn = true;
  }
}

/** Record a product event, e.g. track('search_submitted', { to: 'INR' }). */
export function track(event: string, props?: Record<string, unknown>): void {
  if (posthogOn) posthog.capture(event, props);
}

/** Link events and errors to a signed-in user by id only. Never send name or email. */
export function identifyUser(user: Pick<User, 'id'> | null | undefined): void {
  if (!user) return;
  if (posthogOn) posthog.identify(String(user.id));
  if (SENTRY_DSN) Sentry.setUser({ id: String(user.id) });
}

export function resetAnalytics(): void {
  if (posthogOn) posthog.reset();
  if (SENTRY_DSN) Sentry.setUser(null);
}

export { Sentry };
