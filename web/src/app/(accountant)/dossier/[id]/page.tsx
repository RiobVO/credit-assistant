import { Topbar } from "../../_components/topbar";

import { ActionBar } from "./_components/action-bar";
import { BorrowerCard } from "./_components/borrower-card";
import { KpiRow } from "./_components/kpi-row";
import { Revenue24mChart } from "./_components/revenue-24m-chart";
import { RiskSignals } from "./_components/risk-signals";
import { ScoreGauge } from "./_components/score-gauge";
import { SubHeader } from "./_components/sub-header";
import { mockDossier } from "./_lib/mock-dossier";

// Phase 3.A — UI с mock-данными. На Phase 3.B страница станет async с
// useQuery → GET /api/dossier/{id}; layout уже сейчас спроектирован под него.
export default async function DossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data = mockDossier(id);

  const breadcrumbs = [
    { label: "Заявки" },
    { label: "Досье" },
    { label: data.application.id, current: true },
  ];

  return (
    <>
      <Topbar crumbs={breadcrumbs} />
      <div className="w-full max-w-[1280px] px-8 pt-7 pb-12">
        <SubHeader
          applicationId={data.application.id}
          borrowerName={data.borrower.name}
          status={data.application.status}
          documentsCount={5}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <ScoreGauge
            score={data.risk_score.score}
            recommendation={data.risk_score.recommendation}
          />
          <BorrowerCard borrower={data.borrower} />
        </div>

        <div className="mt-4">
          <KpiRow kpis={data.kpis} />
        </div>

        <div className="mt-4">
          <Revenue24mChart data={data.monthly_revenue_24m} />
        </div>

        <div className="mt-4">
          <RiskSignals flags={data.red_flags} />
        </div>

        <ActionBar />
      </div>
    </>
  );
}
