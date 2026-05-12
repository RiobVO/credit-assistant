"use client";

// Client-обёртка над страницей досье: fetch через TanStack Query +
// suspense skeleton + error UI (404 / network / 500). Layout повторяет
// дизайн-таргет (web/design-reference/2026-05-13-target-state-preview.html,
// сцена «dossier»): чистый header + score+borrower + 4 KPI (Готовность 4-я)
// + chart + risk-signals. Без нижнего ActionBar — действия в шапке.

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { BorrowerCard } from "./borrower-card";
import { DossierError } from "./dossier-error";
import { DossierSkeleton } from "./dossier-skeleton";
import { KpiRow } from "./kpi-row";
import { Revenue24mChart } from "./revenue-24m-chart";
import { RiskSignals } from "./risk-signals";
import { ScoreGauge } from "./score-gauge";
import { SubHeader } from "./sub-header";

import { getDossier } from "@/lib/api";
import { useAppMode } from "@/lib/use-app-mode";

export function DossierView({ dossierId }: { dossierId: string }) {
  const mode = useAppMode();
  const t = useTranslations("dossier");
  const query = useQuery({
    queryKey: ["dossier", dossierId],
    queryFn: () => getDossier(dossierId),
    retry: 1,
  });

  if (query.isPending) {
    return <DossierSkeleton />;
  }

  if (query.isError) {
    const back =
      mode === "bank"
        ? { href: "/history", label: t("back_to_history") }
        : { href: "/manual-input", label: t("back_to_form") };
    return (
      <DossierError
        dossierId={dossierId}
        error={query.error}
        onRetry={() => query.refetch()}
        backHref={back.href}
        backLabel={back.label}
      />
    );
  }

  const data = query.data;

  return (
    <div className="mx-auto w-full max-w-[1280px] px-8 pt-7 pb-12">
      <SubHeader dossierId={dossierId} borrower={data.borrower} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <ScoreGauge
          score={data.risk_score.display_score}
          recommendation={data.risk_score.recommendation}
        />
        <BorrowerCard borrower={data.borrower} />
      </div>

      <div className="mt-4">
        <KpiRow kpis={data.kpis} dossierId={dossierId} />
      </div>

      <div className="mt-4">
        <Revenue24mChart
          data={data.monthly_revenue_24m}
          hasAnnualRevenue={data.kpis.revenue_ltm !== null}
        />
      </div>

      <div className="mt-4">
        <RiskSignals flags={data.red_flags} rulesEvaluated={data.rules_evaluated} />
      </div>
    </div>
  );
}
