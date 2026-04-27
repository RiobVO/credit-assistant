"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import { FormProvider, useForm } from "react-hook-form";

import { ApiError, postManualInput } from "@/lib/api";

import { Topbar, type DraftIndicator } from "@/components/topbar";

import { FormFooter } from "./components/form-footer";
import { InfoBanner } from "./components/info-banner";
import { PageHead } from "./components/page-head";
import { Stepper } from "./components/stepper";
import { Step1Borrower } from "./components/step-1-borrower";
import { Step2Financials } from "./components/step-2-financials";
import { Step3Loan } from "./components/step-3-loan";
import { formValuesToPayload } from "./form-mapper";
import { useFormDraft } from "./hooks/use-form-draft";
import { SourceTrailProvider } from "./hooks/use-source-trail";
import { defaultFormValues, formSchema, type FormValues } from "./schema";

type Step = 1 | 2 | 3;

const STEP_TITLE: Record<Step, string> = {
  1: "Шаг 1 — Основные данные",
  2: "Шаг 2 — Финансовые показатели",
  3: "Шаг 3 — Параметры кредита",
};

const STEP_BANNER: Record<Step, "registry" | "financials" | "final"> = {
  1: "registry",
  2: "financials",
  3: "final",
};

// CA-018: extract из (accountant)/manual-input/page.tsx. Чтобы один и тот же
// route работал в обоих режимах (bank/accountant) с правильным sidebar,
// view вынесен в features/, а chrome решается AppShell на уровне layout.
export function ManualInputView() {
  // useSearchParams требует Suspense-границы во время prerender Next App Router.
  return (
    <Suspense fallback={<ManualInputFallback />}>
      <ManualInputPageInner />
    </Suspense>
  );
}

function ManualInputFallback() {
  return (
    <div className="w-full max-w-[1180px] px-8 pt-7 pb-[120px]">
      <div className="rounded-lg border border-[var(--ca-border)] bg-[var(--ca-surface)] px-5 py-4 text-[13px] text-[var(--ca-ink-500)]">
        Загружаем форму…
      </div>
    </div>
  );
}

function ManualInputPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Считываем draft id один раз: повторное чтение search params на каждый rerender
  // привело бы к лишнему GET после нашего же replaceState.
  const [initialDraftId] = useState<string | null>(
    () => searchParams?.get("draft") ?? null,
  );

  const [step, setStep] = useState<Step>(1);

  // caseId генерится только на клиенте — Math.random() в SSR не совпадает
  // с первым клиентским рендером и ловит hydration mismatch.
  // useSyncExternalStore возвращает null на сервере и стабильный id на клиенте.
  const caseId = useSyncExternalStore(
    () => () => {},
    () => getClientCaseId(),
    () => null,
  );

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: defaultFormValues(),
    mode: "onTouched",
  });

  const draft = useFormDraft({ form, initialDraftId });

  // Битый/просроченный draft — чистим query, чтобы reload не подбирал его снова.
  useEffect(() => {
    if (draft.loadFailed && initialDraftId !== null) {
      replaceDraftQuery(null);
    }
  }, [draft.loadFailed, initialDraftId]);

  // После первого POST (draftId появился) — пишем его в URL.
  useEffect(() => {
    if (draft.draftId === null) return;
    const current = new URLSearchParams(window.location.search).get("draft");
    if (current !== draft.draftId) {
      replaceDraftQuery(draft.draftId);
    }
  }, [draft.draftId]);

  const submitMutation = useMutation({
    mutationFn: postManualInput,
    onSuccess: (data) => {
      router.push(`/dossier/${data.dossier_id}`);
    },
  });

  const goNext = useCallback(async () => {
    const stepKey = `step${step}` as const;
    const ok = await form.trigger(stepKey);
    if (!ok) return;
    if (step === 3) {
      const values = form.getValues();
      submitMutation.mutate(formValuesToPayload(values));
      return;
    }
    // Save до перехода — fire-and-forget, переход не ждёт сети.
    draft.saveDraft(form.getValues());
    setStep((s) => (s === 1 ? 2 : 3));
  }, [form, submitMutation, step, draft]);

  const goBack = useCallback(() => {
    if (step === 3) setStep(2);
    else if (step === 2) setStep(1);
  }, [step]);

  const breadcrumbs = useMemo(
    () => [
      { label: "Заявки" },
      { label: "Новая заявка" },
      { label: STEP_TITLE[step], current: true },
    ],
    [step],
  );

  const draftIndicator: DraftIndicator = useMemo(() => {
    if (draft.isSaving) return { state: "saving" };
    if (draft.saveError) return { state: "error" };
    if (draft.savedAt) return { state: "saved", at: draft.savedAt };
    return { state: "idle" };
  }, [draft.isSaving, draft.saveError, draft.savedAt]);

  return (
    <FormProvider {...form}>
      <SourceTrailProvider>
      <Topbar crumbs={breadcrumbs} draft={draftIndicator} />
      <div className="w-full max-w-[1180px] px-8 pt-7 pb-[120px]">
        <PageHead caseId={caseId} />

        {draft.isLoading ? (
          <div className="rounded-lg border border-[var(--ca-border)] bg-[var(--ca-surface)] px-5 py-4 text-[13px] text-[var(--ca-ink-500)]">
            Загружаем черновик…
          </div>
        ) : (
          <>
            <Stepper activeStep={step} />
            <InfoBanner variant={STEP_BANNER[step]} />
            {submitMutation.isError ? <ErrorBanner error={submitMutation.error} /> : null}

            {step === 1 ? <Step1Borrower /> : null}
            {step === 2 ? <Step2Financials /> : null}
            {step === 3 ? <Step3Loan /> : null}

            <FormFooter
              variant={`step${step}` as const}
              onCancel={() => form.reset(defaultFormValues())}
              onBack={goBack}
              onNext={goNext}
              isSubmitting={submitMutation.isPending || submitMutation.isSuccess}
            />
          </>
        )}
      </div>
      </SourceTrailProvider>
    </FormProvider>
  );
}

function replaceDraftQuery(draftId: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (draftId === null) {
    url.searchParams.delete("draft");
  } else {
    url.searchParams.set("draft", draftId);
  }
  // history.replaceState вместо router.replace: мы не хотим триггерить
  // server roundtrip / re-render Next-роутера на каждый сейв.
  window.history.replaceState(window.history.state, "", url.toString());
}

function ErrorBanner({ error }: { error: unknown }) {
  let body: string;
  if (error instanceof ApiError) {
    if (typeof error.body === "string") {
      body = error.body || `HTTP ${error.status}`;
    } else if (error.body?.detail) {
      body = JSON.stringify(error.body.detail, null, 2);
    } else {
      body = `HTTP ${error.status}`;
    }
  } else if (error instanceof Error) {
    body = error.message;
  } else {
    body = "Неизвестная ошибка";
  }

  return (
    <div className="mb-[22px] rounded-lg border border-[#F2BCBA] bg-[#FCE7E5] px-[14px] py-3">
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-px size-4 flex-none text-[var(--ca-danger)]" />
        <div className="text-[13px] leading-[1.5] text-[var(--ca-danger)]">
          <b className="font-semibold">Ошибка отправки на скоринг.</b>{" "}
          Проверьте данные и попробуйте снова.
          <pre className="mt-2 max-h-40 overflow-auto rounded-md border border-[#F2BCBA] bg-[var(--ca-surface)] p-2 font-mono text-[11.5px] text-[var(--ca-ink-700)]">
            {body}
          </pre>
        </div>
      </div>
    </div>
  );
}

// Клиентский singleton: caseId один на mount-сессию, переживает rerender'ы,
// но не shared между tab'ами. Реальный caseId придёт с бэкенда после
// создания заявки в Phase 4 (Bank Mode); сейчас это чисто визуальный placeholder.
let cachedClientCaseId: string | null = null;

function getClientCaseId(): string {
  if (cachedClientCaseId !== null) return cachedClientCaseId;
  const now = new Date();
  const year = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const rand = Math.floor(Math.random() * 100000)
    .toString()
    .padStart(5, "0");
  cachedClientCaseId = `CR-${year}-${mm}${dd}-${rand}`;
  return cachedClientCaseId;
}
