"use client";

// Client-обёртка над страницей досье: fetch через TanStack Query +
// suspense skeleton + error UI (404 / network / 500). Layout повторяет
// структуру из дизайна `пдф.png` (banking dashboard) и совпадает со
// скелетом, чтобы переход на готовые данные не «прыгал».

import { useQuery } from "@tanstack/react-query";

import { ActionBar } from "./action-bar";
import { BorrowerCard } from "./borrower-card";
import { DossierError } from "./dossier-error";
import { DossierSkeleton } from "./dossier-skeleton";
import { KpiRow } from "./kpi-row";
import { ReadinessBadge } from "./readiness-badge";
import { Revenue24mChart } from "./revenue-24m-chart";
import { RiskSignals } from "./risk-signals";
import { ScoreGauge } from "./score-gauge";
import { SubHeader } from "./sub-header";

import { getDossier } from "@/lib/api";

export function DossierView({ dossierId }: { dossierId: string }) {
  const query = useQuery({
    queryKey: ["dossier", dossierId],
    queryFn: () => getDossier(dossierId),
    retry: 1,
  });

  if (query.isPending) {
    return <DossierSkeleton />;
  }

  if (query.isError) {
    return (
      <DossierError
        dossierId={dossierId}
        error={query.error}
        onRetry={() => query.refetch()}
      />
    );
  }

  const data = query.data;

  return (
    <div className="mx-auto w-full max-w-[1280px] px-8 pt-7 pb-12">
      <SubHeader
          applicationId={data.application.id}
          borrowerName={data.borrower.name}
          status={data.application.status}
          documentsCount={data.application.documents_count}
        />

        <ReadinessBadge dossierId={dossierId} />

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <ScoreGauge
            score={data.risk_score.display_score}
            recommendation={data.risk_score.recommendation}
          />
          <BorrowerCard borrower={data.borrower} />
        </div>

        <div className="mt-4">
          <KpiRow kpis={data.kpis} />
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

        <ActionBar dossierId={dossierId} borrower={data.borrower} />
    </div>
  );
}
