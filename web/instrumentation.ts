/**
 * T3.1.2 — Sentry/GlitchTip instrumentation for Next.js server runtime.
 *
 * Активируется только когда задан ``SENTRY_DSN`` env. Default off — никаких
 * сетевых обращений из коробки. GlitchTip on-prem (Sentry SaaS forbidden
 * per PROJECT_BRIEF Sec 8) обслуживает Sentry-compatible protocol.
 */

import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const dsn = process.env.SENTRY_DSN;
    if (!dsn) return;

    Sentry.init({
      dsn,
      environment: process.env.SENTRY_ENVIRONMENT ?? "local",
      release: process.env.SENTRY_RELEASE,
      sendDefaultPii: false,
      tracesSampleRate: 0,
    });
  }
}

export const onRequestError = Sentry.captureRequestError;
