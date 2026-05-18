/**
 * T3.1.2 — Sentry/GlitchTip instrumentation for browser runtime.
 *
 * ``NEXT_PUBLIC_SENTRY_DSN`` пробрасывается в bundle при build.
 * ``replaysSessionSampleRate=0`` — banking UI privacy, никогда не
 * записываем DOM mutations.
 */

import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "local",
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
    sendDefaultPii: false,
    tracesSampleRate: 0,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
