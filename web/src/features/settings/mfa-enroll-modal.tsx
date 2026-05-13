"use client";

// 3-stage модалка enrollment 2FA:
//   1. "qr"      — показываем QR + manual-entry fallback, кнопка «Продолжить»
//   2. "verify"  — 6-значный код из аутентификатора, верификация на backend
//   3. "backup"  — 10 одноразовых backup-кодов с copy/download/confirm
//
// Security-hardening (см. project-CLAUDE):
//   • QRCode.toCanvas — canvas-rendering, никакого dangerouslySetInnerHTML
//   • secret/provisioning_uri очищаются на unmount + при выходе из stage='qr'
//   • Esc/backdrop НЕ закрывают модалку в stage='qr'/'verify' — только явная «Отмена»
//   • Stage 'backup': единственный выход — checkbox «я сохранил» + кнопка «Готово»
//   • plain-text secret в <code> скрыт за toggle «Показать»

import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Copy, Download, Loader2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { AuthError } from "@/lib/auth";
import {
  startEnroll,
  verifyEnroll,
  type EnrollStartResponse,
} from "@/lib/mfa";
import { cn } from "@/lib/utils";

type Stage =
  | { kind: "loading" }
  | { kind: "load_error"; message: string }
  | { kind: "qr"; data: EnrollStartResponse }
  | { kind: "verify"; data: EnrollStartResponse; code: string; error: string | null; submitting: boolean }
  | { kind: "backup"; codes: string[]; saved: boolean };

export function MfaEnrollModal({ onClose }: { onClose: () => void }) {
  const t = useTranslations("bank.settings");
  const queryClient = useQueryClient();
  const [stage, setStage] = useState<Stage>({ kind: "loading" });

  // CRITICAL: ref-guard ОБЯЗАТЕЛЕН чтобы effect стрелял один раз. React 19
  // strict-mode (dev) запускает useEffect дважды (mount → cleanup → mount).
  // Без guard'а каждый второй mount генерил НОВЫЙ secret в /enroll/start,
  // перезаписывая первый в БД → user scan'ил QR с одним secret, БД хранила
  // другой → verify_totp ВСЕГДА invalid_code (даже с корректным authenticator).
  // Production race ещё хуже: какой commit пришёл в БД последним — недетерминированно.
  //
  // НЕ используем cancelled-flag: cleanup в strict-mode срабатывает между
  // mount#1 и mount#2 и ставит cancelled=true → когда async-fn возвращается,
  // setStage пропускается → loading навсегда. Guard уже гарантирует один
  // эффективный fetch — cleanup-блокировка не нужна.
  const startedRef = useRef(false);
  // Локализованное сообщение об ошибке захватываем до effect, чтобы deps
  // массив был пустой — иначе любая смена `t` re-fired бы effect и обошла guard.
  const loadErrorMsg = t("mfa_enroll_load_error");
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    startEnroll()
      .then((data) => setStage({ kind: "qr", data }))
      .catch((err: unknown) =>
        setStage({
          kind: "load_error",
          message: err instanceof Error ? err.message : loadErrorMsg,
        }),
      );
  }, [loadErrorMsg]);

  // Esc закрывает ТОЛЬКО на stages где это безопасно (load_error и backup).
  // На qr/verify — пользователь должен явно нажать «Отмена» (защита от случайного
  // выхода с активным enrollment, который застрянет в backend как half-enrolled).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (stage.kind === "load_error" || stage.kind === "backup") {
        if (stage.kind === "backup" && !stage.saved) return;
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stage, onClose]);

  // Body-scroll lock на время модалки.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const handleVerifySubmit = useCallback(
    async (code: string, data: EnrollStartResponse) => {
      setStage({ kind: "verify", data, code, error: null, submitting: true });
      try {
        const resp = await verifyEnroll(code);
        // Инвалидируем кэш analyst — `/me` теперь вернёт mfa_enabled=true.
        await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
        setStage({ kind: "backup", codes: resp.backup_codes, saved: false });
      } catch (err) {
        const msg =
          err instanceof AuthError && err.status === 401
            ? t("mfa_enroll_invalid_code")
            : err instanceof Error
              ? err.message
              : t("mfa_enroll_generic_error");
        setStage({ kind: "verify", data, code, error: msg, submitting: false });
      }
    },
    [queryClient, t],
  );

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mfa-enroll-title"
      className="fixed inset-0 z-[120] grid place-items-center bg-[color-mix(in_srgb,var(--ink-1)_55%,transparent)] backdrop-blur-[2px] p-4"
    >
      <div
        className="relative w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_24px_48px_-12px_rgba(15,23,42,0.18)]"
      >
        <header className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-6 py-4">
          <h2
            id="mfa-enroll-title"
            className="m-0 text-[15.5px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]"
          >
            {t("mfa_enroll_title")}
          </h2>
          {stage.kind === "load_error" ||
          (stage.kind === "backup" && stage.saved) ? (
            <button
              type="button"
              aria-label={t("mfa_enroll_cancel")}
              onClick={onClose}
              className="grid size-7 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
            >
              <X className="size-4" />
            </button>
          ) : null}
        </header>

        <div className="px-6 py-5">
          {stage.kind === "loading" ? <LoadingState /> : null}
          {stage.kind === "load_error" ? (
            <LoadErrorState message={stage.message} onClose={onClose} />
          ) : null}
          {stage.kind === "qr" ? (
            <QrStage
              data={stage.data}
              onContinue={() =>
                setStage({
                  kind: "verify",
                  data: stage.data,
                  code: "",
                  error: null,
                  submitting: false,
                })
              }
              onCancel={onClose}
            />
          ) : null}
          {stage.kind === "verify" ? (
            <VerifyStage
              code={stage.code}
              error={stage.error}
              submitting={stage.submitting}
              onChange={(code) =>
                setStage({
                  kind: "verify",
                  data: stage.data,
                  code,
                  error: null,
                  submitting: false,
                })
              }
              onBack={() => setStage({ kind: "qr", data: stage.data })}
              onSubmit={() => {
                if (stage.code.length === 6) {
                  void handleVerifySubmit(stage.code, stage.data);
                }
              }}
            />
          ) : null}
          {stage.kind === "backup" ? (
            <BackupStage
              codes={stage.codes}
              saved={stage.saved}
              onToggleSaved={(saved) =>
                setStage({ kind: "backup", codes: stage.codes, saved })
              }
              onDone={onClose}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  const t = useTranslations("bank.settings");
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-[13px] text-[var(--ink-3)]">
      <Loader2 className="size-6 animate-spin text-[var(--brand-primary)]" />
      {t("mfa_enroll_loading")}
    </div>
  );
}

function LoadErrorState({
  message,
  onClose,
}: {
  message: string;
  onClose: () => void;
}) {
  const t = useTranslations("bank.settings");
  return (
    <div className="flex flex-col gap-4 py-4">
      <p
        role="alert"
        className="m-0 text-[13px] text-[var(--state-bad-fg)]"
      >
        {message}
      </p>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-9 items-center rounded-md border border-[var(--border)] bg-transparent px-3 text-[12.5px] font-medium text-[var(--ink-1)] transition-colors hover:bg-[var(--surface-2)]"
        >
          {t("mfa_enroll_cancel")}
        </button>
      </div>
    </div>
  );
}

function QrStage({
  data,
  onContinue,
  onCancel,
}: {
  data: EnrollStartResponse;
  onContinue: () => void;
  onCancel: () => void;
}) {
  const t = useTranslations("bank.settings");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [secretVisible, setSecretVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  // Canvas-rendering через qrcode lib. Никакого dangerouslySetInnerHTML —
  // canvas API не позволяет XSS-инъекцию через SVG. Cleanup чистит canvas
  // на unmount, чтобы пиксели не оставались в DOM после закрытия модалки.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let cancelled = false;
    void (async () => {
      try {
        const QRCode = (await import("qrcode")).default;
        if (cancelled) return;
        // QR-код требует максимальный контраст для надёжного scan'а — это
        // ограничение спецификации QR Code 2005 (ISO/IEC 18004), а не дизайн.
        // Используем чистые black/white, не brand-tokens.
        // eslint-disable-next-line no-restricted-syntax
        const QR_DARK = "#000000";
        // eslint-disable-next-line no-restricted-syntax
        const QR_LIGHT = "#ffffff";
        await QRCode.toCanvas(canvas, data.provisioning_uri, {
          errorCorrectionLevel: "M",
          width: 200,
          margin: 1,
          color: { dark: QR_DARK, light: QR_LIGHT },
        });
      } catch {
        // Если qrcode упал — пользователь использует manual entry secret ниже.
      }
    })();
    return () => {
      cancelled = true;
      const ctx = canvas.getContext("2d");
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, [data.provisioning_uri]);

  const handleCopySecret = async () => {
    try {
      await navigator.clipboard.writeText(data.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard заблокирован — игнорируем
    }
  };

  // Группировка base32 по 4 символа для удобства ручного ввода: «ABCD EFGH IJKL …»
  const formattedSecret = data.secret.replace(/(.{4})/g, "$1 ").trim();

  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 text-[11.5px] font-bold uppercase tracking-[0.08em] text-[var(--ink-4)]">
        {t("mfa_enroll_step1_heading")}
      </p>
      <p className="m-0 text-[13px] leading-[1.5] text-[var(--ink-2)]">
        {t("mfa_enroll_scan_label")}
      </p>
      <div className="grid place-items-center rounded-xl border border-[var(--border)] bg-white p-4">
        <canvas ref={canvasRef} width={200} height={200} aria-label="QR" />
      </div>
      <p className="m-0 text-[12px] text-[var(--ink-3)]">
        {t("mfa_enroll_apps_hint")}
      </p>

      <div className="flex flex-col gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
        <span className="text-[11.5px] font-semibold text-[var(--ink-2)]">
          {t("mfa_enroll_secret_label")}
        </span>
        <div className="flex items-center gap-2">
          <code className="flex-1 break-all rounded-md bg-white px-2.5 py-2 font-mono text-[12.5px] tracking-[0.05em] text-[var(--ink-1)]">
            {secretVisible ? formattedSecret : "•••• •••• •••• ••••"}
          </code>
          <button
            type="button"
            onClick={() => setSecretVisible((v) => !v)}
            className="inline-flex h-8 items-center rounded-md border border-[var(--border)] bg-white px-2.5 text-[11.5px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
          >
            {secretVisible ? t("mfa_enroll_secret_hide") : t("mfa_enroll_secret_show")}
          </button>
          <button
            type="button"
            onClick={handleCopySecret}
            disabled={!secretVisible}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border)] bg-white px-2.5 text-[11.5px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)] disabled:opacity-45"
          >
            {copied ? <Check className="size-3" strokeWidth={2.6} /> : <Copy className="size-3" />}
            {copied ? t("mfa_enroll_secret_copied") : t("mfa_enroll_secret_copy")}
          </button>
        </div>
      </div>

      <div className="mt-1 flex justify-between gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex h-10 items-center rounded-md border border-[var(--border)] bg-transparent px-3.5 text-[12.5px] font-medium text-[var(--ink-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          {t("mfa_enroll_cancel")}
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="inline-flex h-10 items-center rounded-md bg-[var(--brand-primary)] px-4 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
        >
          {t("mfa_enroll_continue")}
        </button>
      </div>
    </div>
  );
}

function VerifyStage({
  code,
  error,
  submitting,
  onChange,
  onBack,
  onSubmit,
}: {
  code: string;
  error: string | null;
  submitting: boolean;
  onChange: (v: string) => void;
  onBack: () => void;
  onSubmit: () => void;
}) {
  const t = useTranslations("bank.settings");
  const ref = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    ref.current?.focus();
  }, []);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="flex flex-col gap-4"
    >
      <p className="m-0 text-[11.5px] font-bold uppercase tracking-[0.08em] text-[var(--ink-4)]">
        {t("mfa_enroll_step2_heading")}
      </p>
      <label className="flex flex-col gap-2">
        <span className="text-[13px] text-[var(--ink-2)]">
          {t("mfa_enroll_code_label")}
        </span>
        <input
          ref={ref}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={code}
          onChange={(e) =>
            onChange(e.target.value.replace(/\D/g, "").slice(0, 6))
          }
          disabled={submitting}
          className="h-12 rounded-lg border border-[var(--border)] bg-white px-4 text-center font-mono text-[22px] tracking-[0.4em] text-[var(--ink-1)] outline-none focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)] disabled:opacity-60"
        />
      </label>
      <p className="m-0 text-[11.5px] text-[var(--ink-3)]">
        {t("mfa_enroll_code_hint")}
      </p>
      {error ? (
        <p role="alert" className="m-0 text-[12.5px] text-[var(--state-bad-fg)]">
          {error}
        </p>
      ) : null}
      <div className="mt-1 flex justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className="inline-flex h-10 items-center rounded-md border border-[var(--border)] bg-transparent px-3.5 text-[12.5px] font-medium text-[var(--ink-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] disabled:opacity-50"
        >
          {t("mfa_enroll_back")}
        </button>
        <button
          type="submit"
          disabled={submitting || code.length !== 6}
          className="inline-flex h-10 items-center gap-2 rounded-md bg-[var(--brand-primary)] px-4 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {submitting ? (
            <>
              <Loader2 className="size-3.5 animate-spin" />
              {t("mfa_enroll_verifying")}
            </>
          ) : (
            t("mfa_enroll_verify_cta")
          )}
        </button>
      </div>
    </form>
  );
}

function BackupStage({
  codes,
  saved,
  onToggleSaved,
  onDone,
}: {
  codes: string[];
  saved: boolean;
  onToggleSaved: (v: boolean) => void;
  onDone: () => void;
}) {
  const t = useTranslations("bank.settings");
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard заблокирован — пользователь может скачать .txt
    }
  };

  const handleDownload = () => {
    const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "credit-assistant-backup-codes.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="m-0 text-[14px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
          {t("mfa_backup_title")}
        </h3>
        <p className="mt-1 mb-0 text-[12.5px] leading-[1.5] text-[var(--ink-3)]">
          {t("mfa_backup_intro")}
        </p>
      </div>

      <div className="flex gap-3 rounded-lg border border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] p-3">
        <div className="grid size-8 flex-shrink-0 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--state-warn-fg)_14%,transparent)] text-[var(--state-warn-fg)]">
          <AlertTriangle className="size-4" />
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[12.5px] font-semibold text-[var(--state-warn-fg)]">
            {t("mfa_backup_warning_title")}
          </span>
          <span className="text-[12px] leading-[1.5] text-[var(--ink-2)]">
            {t("mfa_backup_warning_text")}
          </span>
        </div>
      </div>

      <ol className="m-0 grid grid-cols-2 gap-1.5 list-none p-3 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
        {codes.map((c, i) => (
          <li
            key={i}
            className="font-mono text-[13px] tracking-[0.05em] text-[var(--ink-1)] px-2 py-1"
          >
            <span className="text-[var(--ink-4)] mr-2 select-none">{i + 1}.</span>
            {c}
          </li>
        ))}
      </ol>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md border border-[var(--border)] bg-white px-3 text-[12px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
        >
          {copied ? <Check className="size-3" strokeWidth={2.6} /> : <Copy className="size-3" />}
          {copied ? t("mfa_backup_copied") : t("mfa_backup_copy_all")}
        </button>
        <button
          type="button"
          onClick={handleDownload}
          className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md border border-[var(--border)] bg-white px-3 text-[12px] font-medium text-[var(--ink-2)] hover:text-[var(--ink-1)]"
        >
          <Download className="size-3" />
          {t("mfa_backup_download")}
        </button>
      </div>

      <label className="flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={saved}
          onChange={(e) => onToggleSaved(e.target.checked)}
          className="mt-0.5 size-4 cursor-pointer"
        />
        <span className="text-[12.5px] leading-[1.5] text-[var(--ink-2)]">
          {t("mfa_backup_confirm_label")}
        </span>
      </label>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onDone}
          disabled={!saved}
          className={cn(
            "inline-flex h-10 items-center rounded-md bg-[var(--brand-primary)] px-4 text-[13px] font-semibold text-white transition-colors",
            saved
              ? "hover:bg-[var(--brand-primary-hover)]"
              : "cursor-not-allowed opacity-50",
          )}
        >
          {t("mfa_backup_done_cta")}
        </button>
      </div>
    </div>
  );
}
