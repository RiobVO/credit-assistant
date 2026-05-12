"use client";

// T0.3 (Phase A) — manual upload ГНК-справки. Аналитик банка прикладывает
// PDF/JPG + вручную вводит full_name / status / okveds / optional cert_id.
// Optional secition в Step 1: показывается только когда ИНН валидный
// (9 цифр), не блокирующая поле. После успешной загрузки — read-only summary
// с возможностью «загрузить заново».
//
// Phase B (CA-DS28 public lookup) переиспользует тот же UI с pre-fill полей
// из ГНК ответа — этот компонент будет принимать `prefill?: GnkCertificateDto`.

import { CheckCircle2, FileUp, Loader2, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  type GnkCertificateDto,
  type GnkStatus,
  type GnkUploadInput,
  getGnkCertificate,
  uploadGnkCertificate,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIMES = ["application/pdf", "image/jpeg", "image/png"] as const;

const STATUS_OPTIONS: GnkStatus[] = ["active", "suspended", "revoked", "unknown"];

type Props = {
  inn: string;
  /** true когда ИНН ≥ 9 цифр прошёл базовую client-side валидацию */
  innValid: boolean;
};

export function GnkCertificateUpload({ inn, innValid }: Props) {
  const t = useTranslations("accountant.manual_input.gnk");
  const [existing, setExisting] = useState<GnkCertificateDto | null>(null);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fullName, setFullName] = useState("");
  const [status, setStatus] = useState<GnkStatus>("active");
  const [okveds, setOkveds] = useState("");
  const [certId, setCertId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // При смене ИНН — pre-fetch latest. Если уже была загружена справка, показываем
  // её summary и сворачиваем форму. Аналитик может «загрузить заново» при изменениях.
  useEffect(() => {
    if (!innValid) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync с props
      setExisting(null);
      return;
    }
    let cancelled = false;
    setLoadingExisting(true);
    getGnkCertificate(inn)
      .then((cert) => {
        if (!cancelled) setExisting(cert);
      })
      .catch(() => {
        // 4xx/5xx — silent fail. Аналитик увидит пустую форму, может загрузить вручную.
      })
      .finally(() => {
        if (!cancelled) setLoadingExisting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [inn, innValid]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0] ?? null;
    if (picked === null) {
      setFile(null);
      return;
    }
    if (picked.size > MAX_BYTES) {
      setError(t("err_too_large"));
      setFile(null);
      return;
    }
    if (!ALLOWED_MIMES.includes(picked.type as (typeof ALLOWED_MIMES)[number])) {
      setError(t("err_bad_mime"));
      setFile(null);
      return;
    }
    setError(null);
    setFile(picked);
  }, [t]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!file || !fullName.trim() || !innValid) return;
      setSubmitting(true);
      setError(null);
      try {
        const payload: GnkUploadInput = {
          inn,
          file,
          fullName: fullName.trim(),
          status,
          okveds: okveds
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          certId: certId.trim() || null,
        };
        const saved = await uploadGnkCertificate(payload);
        setExisting(saved);
        // Reset form для возможной повторной загрузки.
        setFile(null);
        if (inputRef.current) inputRef.current.value = "";
      } catch (err) {
        setError(err instanceof Error ? err.message : t("err_upload"));
      } finally {
        setSubmitting(false);
      }
    },
    [certId, file, fullName, inn, innValid, okveds, status, t],
  );

  if (!innValid) {
    return (
      <div className="rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-[12px] text-[var(--ink-4)]">
        {t("hint_enter_inn")}
      </div>
    );
  }

  if (existing && !file) {
    return <ExistingCertSummary cert={existing} onReplace={() => setExisting(null)} />;
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3"
      aria-label={t("aria_form")}
    >
      <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--ink-1)]">
        <FileUp className="h-4 w-4 text-[var(--ink-3)]" aria-hidden />
        {t("section_title")}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
        onChange={handleFileChange}
        className="block w-full text-[12px] text-[var(--ink-2)]"
        aria-label={t("aria_file")}
      />

      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="block text-[12px] text-[var(--ink-3)] mb-1">{t("label_name")}</span>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder={t("ph_name")}
            className="w-full rounded-[8px] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[13px]"
            maxLength={500}
            required
          />
        </label>
        <label className="block">
          <span className="block text-[12px] text-[var(--ink-3)] mb-1">{t("label_status")}</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as GnkStatus)}
            className="w-full rounded-[8px] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[13px]"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t(`status_${s}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block col-span-2">
          <span className="block text-[12px] text-[var(--ink-3)] mb-1">{t("label_okveds")}</span>
          <input
            type="text"
            value={okveds}
            onChange={(e) => setOkveds(e.target.value)}
            placeholder={t("ph_okveds")}
            className="w-full rounded-[8px] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[13px]"
          />
        </label>
        <label className="block col-span-2">
          <span className="block text-[12px] text-[var(--ink-3)] mb-1">{t("label_cert_id")}</span>
          <input
            type="text"
            value={certId}
            onChange={(e) => setCertId(e.target.value)}
            placeholder={t("ph_cert_id")}
            className="w-full rounded-[8px] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[13px]"
            maxLength={50}
          />
        </label>
      </div>

      {error !== null && (
        <div className="flex items-start gap-2 rounded-[8px] bg-[var(--state-bad-bg)] px-3 py-2 text-[12px] text-[var(--state-bad-fg)]" role="alert">
          <TriangleAlert className="h-4 w-4 shrink-0 mt-px" aria-hidden />
          {error}
        </div>
      )}

      <div className="flex items-center justify-between">
        {loadingExisting && (
          <span className="text-[11px] text-[var(--ink-4)] inline-flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> {t("checking")}
          </span>
        )}
        <button
          type="submit"
          disabled={!file || !fullName.trim() || submitting}
          className={cn(
            "ml-auto inline-flex items-center gap-2 rounded-[8px] px-4 py-2 text-[13px] font-medium transition-colors",
            "bg-[var(--brand-primary)] text-[var(--brand-ink)] hover:bg-[var(--brand-hover)]",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          {t("btn_upload")}
        </button>
      </div>
    </form>
  );
}

function ExistingCertSummary({
  cert,
  onReplace,
}: {
  cert: GnkCertificateDto;
  onReplace: () => void;
}) {
  const t = useTranslations("accountant.manual_input.gnk");
  const statusKey = `status_${cert.status}` as const;
  return (
    <div
      className="rounded-[10px] border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] px-4 py-3 text-[13px]"
      data-testid="gnk-cert-summary"
    >
      <div className="flex items-center gap-2 font-medium text-[var(--state-ok-fg)]">
        <CheckCircle2 className="h-4 w-4" aria-hidden />
        {t("loaded_title")}
      </div>
      <dl className="mt-2 grid grid-cols-[100px_1fr] gap-x-3 gap-y-1 text-[12px]">
        <dt className="text-[var(--ink-3)]">{t("row_name")}</dt>
        <dd className="text-[var(--ink-1)]">{cert.full_name}</dd>
        <dt className="text-[var(--ink-3)]">{t("row_status")}</dt>
        <dd className="text-[var(--ink-1)]">{t(statusKey)}</dd>
        {cert.okveds.length > 0 && (
          <>
            <dt className="text-[var(--ink-3)]">{t("row_okveds")}</dt>
            <dd className="text-[var(--ink-1)]">{cert.okveds.join(", ")}</dd>
          </>
        )}
        {cert.cert_id && (
          <>
            <dt className="text-[var(--ink-3)]">{t("row_cert_id")}</dt>
            <dd className="text-[var(--ink-1)] font-mono">{cert.cert_id}</dd>
          </>
        )}
      </dl>
      <button
        type="button"
        onClick={onReplace}
        className="mt-3 text-[12px] text-[var(--brand-primary)] hover:underline"
      >
        {t("btn_replace")}
      </button>
    </div>
  );
}
