export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Phase 4: режим инсталляции, синхронизирован с backend ``APP_MODE``.
// Управляет root redirect и видимостью bank-роутов.
export type AppMode = "bank" | "accountant";
export const APP_MODE: AppMode =
  (process.env.NEXT_PUBLIC_APP_MODE as AppMode) ?? "accountant";

// Имена httpOnly cookies, в которые BFF route handlers пакуют JWT.
// Frontend никогда не видит сами токены — только наличие сессии (через /api/auth/me).
export const ACCESS_COOKIE = "ca_access";
export const REFRESH_COOKIE = "ca_refresh";

// Brand tenant id (см. config/brands/<id>.json + ADR-0011). По умолчанию
// производный от APP_MODE: bank → uzbekbank, accountant → default.
export const BRAND_ID: string =
  process.env.NEXT_PUBLIC_BRAND_ID ??
  (APP_MODE === "bank" ? "uzbekbank" : "default");

// CA-063: статическая локаль инсталляции (ru | uz). По умолчанию ru.
// Меняется только в build env, runtime-switch не предусмотрен (один UI-язык
// на банк-инсталляцию).
export const LOCALE: string = process.env.NEXT_PUBLIC_LOCALE ?? "ru";
