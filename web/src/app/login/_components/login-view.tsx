"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  AuthError,
  isMfaChallenge,
  login,
  submitMfaChallenge,
} from "@/lib/auth";

import styles from "./login.module.css";

// Errors переводятся в callsite через `t("email_required")` / etc.
// Zod возвращает короткий sentinel, view замапит на локализованную строку.
const schema = z.object({
  email: z.string().min(3, "email_required").max(255),
  password: z.string().min(1, "password_required").max(200),
});

type FormValues = z.infer<typeof schema>;

export function LoginView() {
  const t = useTranslations("bank.login");
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") ?? "/search";

  const stageRef = useRef<HTMLDivElement | null>(null);
  const [showPass, setShowPass] = useState(false);
  const [remember, setRemember] = useState(true);
  const [serverError, setServerError] = useState<string | null>(null);
  // Step-2 state: backend ответил requires_mfa, нужен TOTP-код.
  // challenge_token живёт 5 минут (см. JWT-сервис), потом backend вернёт 401
  // и пользователь увидит «Срок сессии истёк — войдите заново».
  const [mfaState, setMfaState] = useState<{ challengeToken: string } | null>(
    null,
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  // Cursor-tracked spotlight + parallax. Обновляет CSS-vars на корневом
  // элементе — `.glow` подхватывает позицию, `.card` смещается противоходом.
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = stageRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    el.style.setProperty("--mx", `${x}px`);
    el.style.setProperty("--my", `${y}px`);
    const nx = x / r.width - 0.5;
    const ny = y / r.height - 0.5;
    el.style.setProperty("--px", nx.toFixed(3));
    el.style.setProperty("--py", ny.toFixed(3));
  }, []);

  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    el.style.setProperty("--mx", "38%");
    el.style.setProperty("--my", "48%");
    el.style.setProperty("--px", "0");
    el.style.setProperty("--py", "0");
  }, []);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      const result = await login(values);
      if (isMfaChallenge(result)) {
        // Backend требует второй фактор — переключаемся на MFA-step.
        setMfaState({ challengeToken: result.challenge_token });
        return;
      }
      router.push(nextPath);
      router.refresh();
    } catch (e) {
      if (e instanceof AuthError && e.status === 401) {
        setServerError(t("error_invalid"));
      } else {
        setServerError(t("error_generic"));
      }
    }
  };

  const handleMfaSuccess = () => {
    router.push(nextPath);
    router.refresh();
  };

  const handleMfaBack = () => {
    setMfaState(null);
    setServerError(null);
  };

  return (
    <div
      ref={stageRef}
      className={styles.root}
      onMouseMove={onMouseMove}
      data-screen-label="01 Login"
    >
      <div className={styles.grid} aria-hidden />
      <div className={`${styles.drift} ${styles.driftA}`} aria-hidden />
      <div className={`${styles.drift} ${styles.driftB}`} aria-hidden />
      <div className={styles.glow} aria-hidden />
      <div className={styles.vignette} aria-hidden />

      <header className={styles.head}>
        <div className={styles.brand}>
          <div className={styles.brandMark}>UB</div>
          <div className={styles.brandText}>
            <span className={styles.brandName}>Uzbekbank Credit</span>
            <span className={styles.brandSub}>Bank Mode</span>
          </div>
        </div>
        <div className={styles.headMeta}>
          <span className={styles.statusDot} aria-hidden />
          {t("tls_signal_short")}
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.card}>
          {mfaState ? (
            <MfaStep
              challengeToken={mfaState.challengeToken}
              onSuccess={handleMfaSuccess}
              onBack={handleMfaBack}
            />
          ) : (
            <>
          <div className={styles.eyebrow}>Authentication</div>
          <h1 className={styles.title}>{t("title")}</h1>
          <p className={styles.sub}>{t("subtitle")}</p>

          <form
            onSubmit={handleSubmit(onSubmit)}
            className={styles.form}
            noValidate
          >
            <div className={styles.group}>
              <label className={styles.label} htmlFor="email">
                {t("email_label")}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder="имя@uzbekbank.uz"
                className={styles.input}
                disabled={isSubmitting}
                {...register("email")}
              />
              {errors.email ? (
                <p className={styles.error} role="alert" style={{ marginTop: 6 }}>
                  {t(errors.email.message as "email_required")}
                </p>
              ) : null}
            </div>

            <div className={styles.group}>
              <label className={styles.label} htmlFor="password">
                {t("password_label")}
              </label>
              <div className={styles.field}>
                <input
                  id="password"
                  type={showPass ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••••"
                  className={styles.input}
                  style={{ paddingRight: 40 }}
                  disabled={isSubmitting}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className={styles.suffix}
                  aria-label={showPass ? t("hide_password") : t("show_password")}
                  tabIndex={-1}
                >
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {errors.password ? (
                <p className={styles.error} role="alert" style={{ marginTop: 6 }}>
                  {t(errors.password.message as "password_required")}
                </p>
              ) : null}
            </div>

            <div className={styles.row}>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span>{t("remember")}</span>
              </label>
              <button
                type="button"
                className={styles.forgot}
                onClick={() => {
                  // TODO: реализовать восстановление через /api/auth/recover
                }}
              >
                {t("forgot")}
              </button>
            </div>

            {serverError ? (
              <p className={styles.error} role="alert">
                {serverError}
              </p>
            ) : null}

            <button type="submit" className={styles.cta} disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  {t("submitting")}
                </>
              ) : (
                <>
                  {t("submit")} <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>
            </>
          )}
        </div>
      </main>

      <footer className={styles.foot}>
        <span className={styles.footSecurity}>
          <span className={styles.footDot} aria-hidden />
          {t("tls_signal")}
        </span>
        <span>© 2026 Uzbekbank · Все права защищены</span>
      </footer>
    </div>
  );
}

// Step-2 после успешной верификации пароля: ввод TOTP (6 цифр) либо backup-кода
// (8 буквенно-цифровых символов). challenge_token живёт 5 минут на backend.
function MfaStep({
  challengeToken,
  onSuccess,
  onBack,
}: {
  challengeToken: string;
  onSuccess: () => void;
  onBack: () => void;
}) {
  const t = useTranslations("bank.login");
  const [useBackup, setUseBackup] = useState(false);
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Mount focus только. Reset при switch — в handleToggleBackup ниже, не в effect
  // (избегаем react-hooks/set-state-in-effect).
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleToggleBackup = () => {
    setUseBackup((v) => !v);
    setCode("");
    setError(null);
    // Перевод фокуса на input в следующем tick'е, после ре-рендера.
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const maxLen = useBackup ? 12 : 6;
  // TOTP — только цифры; backup-код — alphanumeric (backend генерирует base32-like).
  const sanitize = (raw: string): string =>
    useBackup
      ? raw.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, maxLen)
      : raw.replace(/\D/g, "").slice(0, maxLen);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    const isValid = useBackup ? code.length >= 8 : code.length === 6;
    if (!isValid) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitMfaChallenge({
        challenge_token: challengeToken,
        code,
        use_backup_code: useBackup,
      });
      onSuccess();
    } catch (err) {
      if (err instanceof AuthError) {
        if (err.status === 401) {
          setError(t("mfa_error_invalid"));
        } else if (err.status === 403 || err.status === 400) {
          // 400 — challenge_token expired/invalid; нужно начать с пароля.
          setError(t("mfa_error_expired"));
        } else {
          setError(t("mfa_error_generic"));
        }
      } else {
        setError(t("mfa_error_generic"));
      }
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className={styles.eyebrow}>Authentication · 2FA</div>
      <h1 className={styles.title}>{t("mfa_title")}</h1>
      <p className={styles.sub}>{t("mfa_subtitle")}</p>

      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <div className={styles.group}>
          <label className={styles.label} htmlFor="mfa-code">
            {useBackup ? t("mfa_backup_code_label") : t("mfa_code_label")}
          </label>
          <input
            ref={inputRef}
            id="mfa-code"
            type="text"
            inputMode={useBackup ? "text" : "numeric"}
            autoComplete="one-time-code"
            maxLength={maxLen}
            placeholder={useBackup ? "XXXXXXXX" : "••••••"}
            className={styles.input}
            style={{
              textAlign: "center",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              letterSpacing: useBackup ? "0.18em" : "0.4em",
              fontSize: 20,
            }}
            value={code}
            onChange={(e) => setCode(sanitize(e.target.value))}
            disabled={submitting}
            autoFocus
          />
        </div>

        <button
          type="button"
          onClick={handleToggleBackup}
          className={styles.forgot}
          style={{ textAlign: "left" }}
        >
          {useBackup ? t("mfa_use_authenticator") : t("mfa_use_backup")}
        </button>

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          className={styles.cta}
          disabled={
            submitting || (useBackup ? code.length < 8 : code.length !== 6)
          }
        >
          {submitting ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              {t("mfa_submitting")}
            </>
          ) : (
            <>
              {t("mfa_submit")} <ArrowRight size={15} />
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className={styles.forgot}
          style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
        >
          <ArrowLeft size={13} />
          {t("mfa_back_to_password")}
        </button>
      </form>
    </>
  );
}
