"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthError, login } from "@/lib/auth";

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
      await login(values);
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
