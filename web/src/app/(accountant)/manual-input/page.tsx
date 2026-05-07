"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";

import { ApiError, postManualInput, type DossierResponseDto } from "@/lib/api";

import { Topbar } from "../_components/topbar";

import { DossierResult } from "./_components/dossier-result";
import { FormFooter } from "./_components/form-footer";
import { InfoBanner } from "./_components/info-banner";
import { PageHead } from "./_components/page-head";
import { Stepper } from "./_components/stepper";
import { Step1Borrower } from "./_components/step-1-borrower";
import { Step2Financials } from "./_components/step-2-financials";
import { Step3Loan } from "./_components/step-3-loan";
import { formValuesToPayload } from "./_form-mapper";
import { defaultFormValues, formSchema, type FormValues } from "./_schema";

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

export default function ManualInputPage() {
  const [step, setStep] = useState<Step>(1);
  const [result, setResult] = useState<DossierResponseDto | null>(null);

  const caseId = useMemo(() => generateCaseId(), []);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: defaultFormValues(),
    mode: "onTouched",
  });

  const mutation = useMutation({
    mutationFn: postManualInput,
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const goNext = useCallback(async () => {
    const stepKey = `step${step}` as const;
    const ok = await form.trigger(stepKey);
    if (!ok) return;
    if (step === 3) {
      const values = form.getValues();
      mutation.mutate(formValuesToPayload(values));
      return;
    }
    setStep((s) => (s === 1 ? 2 : 3));
  }, [form, mutation, step]);

  const goBack = useCallback(() => {
    if (step === 3) setStep(2);
    else if (step === 2) setStep(1);
  }, [step]);

  const newApplication = useCallback(() => {
    form.reset(defaultFormValues());
    setResult(null);
    setStep(1);
    mutation.reset();
  }, [form, mutation]);

  const breadcrumbs = useMemo(
    () => [
      { label: "Заявки" },
      { label: "Новая заявка" },
      { label: result ? "Результаты скоринга" : STEP_TITLE[step], current: true },
    ],
    [result, step],
  );

  return (
    <FormProvider {...form}>
      <Topbar crumbs={breadcrumbs} />
      <div className="w-full max-w-[1180px] px-8 pt-7 pb-[120px]">
        <PageHead caseId={caseId} />

        {result ? (
          <DossierResult data={result} onNew={newApplication} />
        ) : (
          <>
            <Stepper activeStep={step} />
            <InfoBanner variant={STEP_BANNER[step]} />
            {mutation.isError ? <ErrorBanner error={mutation.error} /> : null}

            {step === 1 ? <Step1Borrower /> : null}
            {step === 2 ? <Step2Financials /> : null}
            {step === 3 ? <Step3Loan /> : null}

            <FormFooter
              variant={`step${step}` as const}
              onCancel={() => form.reset(defaultFormValues())}
              onBack={goBack}
              onNext={goNext}
              isSubmitting={mutation.isPending}
            />
          </>
        )}
      </div>
    </FormProvider>
  );
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
          <pre className="mt-2 max-h-40 overflow-auto rounded-md border border-[#F2BCBA] bg-white p-2 font-mono text-[11.5px] text-[var(--ca-ink-700)]">
            {body}
          </pre>
        </div>
      </div>
    </div>
  );
}

function generateCaseId(): string {
  const now = new Date();
  const year = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const rand = Math.floor(Math.random() * 100000)
    .toString()
    .padStart(5, "0");
  return `CR-${year}-${mm}${dd}-${rand}`;
}
