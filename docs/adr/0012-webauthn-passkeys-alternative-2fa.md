# ADR 0012: WebAuthn/Passkeys как alternative 2FA factor

- **Status**: Proposed (defer implementation)
- **Date**: 2026-05-16
- **Phase**: post-4
- **CA-DS15**

## Context

Phase 4.B зафиксировала TOTP (RFC 6238) через Microsoft Authenticator как
обязательный второй фактор для bank-mode (`AuthnPort`, `mfa_enrolled_at`,
6-значный код). Эта схема покрывает требования ЦБ РУз для MFA и
сертифицирована Microsoft, но накопила несколько UX-проблем за первые
недели dogfooding:

- **iCloud-cache scenario** (CA-DS14). MS Authenticator **не реплицирует
  TOTP-ключи через Apple iCloud-backup**: восстановление iPhone (новый
  телефон / factory reset) даёт пустой Authenticator, аналитик
  блокируется до admin-reset через compliance. В корпоративном банке
  средне 5-8 таких событий в месяц на 100 аналитиков — заметная
  оперативная нагрузка.
- **Setup friction**: enrollment требует переключения между двумя
  устройствами (десктоп для UI + телефон для камеры), типичное
  завершение ~3 минуты при первом разе. Большая отговорка для
  remote-onboard'инга.
- **Phishing surface**: TOTP-код можно ввести на fake-сайте; не
  origin-bound. Для bank-периметра низкая угроза (on-prem только), но
  как defense-in-depth компонент — слабое звено.
- **Recovery-channel**: единственный путь — admin-reset через
  compliance. Нет user-self-recovery (backup codes отсутствуют — Phase
  4.B решила не плодить факторы; но это значит что MFA-loss == админка).

WebAuthn (FIDO2) / Passkeys решает все четыре пункта одновременно:

- Платформенные authenticator'ы (Touch ID / Windows Hello / iCloud
  Keychain) поддерживают синхронизацию между устройствами того же
  Apple ID / Microsoft account / Google account — recovery «из коробки».
- Setup за 5-10 секунд: один tap на биометрию, без перевода взгляда
  между устройствами.
- Origin-binding встроен в спецификацию — phishing-resistant by design.
- Cross-device через QR-flow (CTAP 2.2 hybrid transport) — можно
  authenticate с телефона на десктоп.

## Decision

**Зафиксировать WebAuthn/Passkeys как roadmap-item, реализацию отложить
до post-pilot Phase 5 / Phase 6.** На текущей фазе мы:

1. **Сохраняем TOTP как primary 2FA-фактор.** Production-bank рассчитывает
   на сертифицированную Microsoft-схему; смена базового фактора в
   pilot-фазе создаёт audit-risk.
2. **Документируем CA-DS14 в `/help`** (FAQ row про phone-change /
   iCloud-cache) — снимаем основной support-channel-вопрос без замены
   фактора.
3. **Не вводим backup codes как промежуточное решение.** Backup codes —
   shared secret, который пользователи распечатывают и теряют; в
   bank-секторе это compliance-risk (printed-on-paper credentials).
   Лучше пройти прямо к WebAuthn чем накапливать legacy.
4. **AuthnPort оставляем закрытым к TOTP-семантике.** Расширение под
   WebAuthn потребует new port methods (register_credential /
   verify_assertion / list_credentials), это breaking change для
   adapters. Делаем в один проход когда пойдём.

## Implementation sketch (deferred)

```
Backend:
- pip add: webauthn (Duo Labs / py_webauthn). FIDO2 server, ~5KB.
- WebAuthnAuthnAdapter implements AuthnPort + 3 new methods:
    register_credential_start(analyst_id) -> challenge
    register_credential_finish(analyst_id, attestation) -> Credential
    verify_assertion(analyst_id, assertion) -> bool
- ORM: webauthn_credentials table (id, analyst_id, credential_id,
  public_key, sign_count, transports, attestation_format, created_at).
- Settings UI: «Add Passkey» button рядом с «Disable 2FA».
- Login flow: prefer Passkey если зарегистрирован, fallback TOTP.

Frontend:
- @simplewebauthn/browser — стандартный helper для navigator.credentials.
- LoginScreen: после email/password — попытка Passkey (silent),
  fallback на TOTP screen.
- SettingsScreen: список Passkeys с device-labels + delete.

Migration:
- Backward-compat: TOTP остаётся для users без Passkey.
- Self-recovery: user с Passkey + TOTP теряет один — login через
  второй; admin-reset нужен только если оба потеряны.
```

## Alternatives considered

- **Backup codes**: rejected (compliance-risk, см. Decision §3).
- **SMS / Email OTP**: rejected. SMS — phishable, SIM-swap attack
  vector; email — assumes сoт corporate access восстановлен (chicken-egg
  с phone-loss).
- **Hardware token (YubiKey)**: viable enterprise option, но требует
  закупки на каждого аналитика (~$40-60/unit), procurement-friction.
  Можно добавить **на одном уровне с Passkey** через тот же WebAuthn
  endpoint — `transports: ['usb']` для hardware vs `transports:
  ['internal']` для platform authenticator.

## Tradeoffs

- (+) Recovery «из коробки» через cloud sync — закрывает CA-DS14.
- (+) Setup за 5-10 сек vs ~3 мин для TOTP.
- (+) Phishing-resistant — соответствует Zero Trust посылке.
- (+) WebAuthn — RFC-стандарт, не vendor lock-in.
- (−) Платформенная фрагментация: Linux desktop без TPM-чипа теряет
  platform authenticator, нужен YubiKey-fallback.
- (−) Поддержка regulator: ЦБ РУз методики пока ссылаются на TOTP /
  SMS / hardware token; WebAuthn явно не упомянут. Перед deployment —
  formal review с compliance.
- (−) Cost of switch: enrollment-flow rewrite, login-flow двухпутевый,
  +2-3 недели dev-time + security review (внешний pen-test
  рекомендуется).

## Migration path (когда пойдём)

1. **Phase 5+ (security hardening sprint)**: реализовать WebAuthn
   adapter + UI, держать TOTP как primary.
2. **Stage 1 (opt-in)**: bank-installation flag `WEBAUTHN_ENABLED`. Только
   pilot-аналитики получают Passkey-кнопку. 2-3 недели наблюдения.
3. **Stage 2 (preferred)**: дефолт переключается — Passkey предлагается
   при first-time setup; TOTP — opt-in.
4. **Stage 3 (TOTP-deprecation)**: после consensus pilot-банка — оставить
   TOTP только как legacy для users без cloud-sync устройств.

## Security checklist (для implementation phase)

- [ ] User Verification Required (`userVerification: 'required'`) — не
      `preferred` (biometric/PIN gate обязателен).
- [ ] `attestation: 'direct'` — собирать attestation для аудита,
      проверять root certs (Apple/Google/MS).
- [ ] Resident keys (`residentKey: 'required'`) — для
      conditional-mediation (browser autofill).
- [ ] Public-key storage: COSE-formatted, **не raw bytes** — изменение
      формата = breaking change.
- [ ] Sign-counter check: monotonically increasing per credential;
      decrease = clone attack, lock credential.
- [ ] Allowlist transports per credential (внутренний vs USB) — иначе
      browser показывает все варианты.
- [ ] CSRF на register/finish endpoints (origin check встроен, но
      также проверять CSRF-token).
- [ ] Audit log per credential event (register / login / delete) с
      attestation hash.

## Decision log

- 2026-05-16: ADR draft (this document). CA-DS15 closed → roadmap-item
  with explicit defer rationale.
