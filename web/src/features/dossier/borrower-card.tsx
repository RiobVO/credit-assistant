import { CheckCircle2 } from "lucide-react";

import type { DossierViewDto } from "@/lib/api";

const LEGAL_FORM_LABEL: Record<DossierViewDto["borrower"]["legal_form"], string> = {
  llc: "ООО / МЧЖ",
  pe: "Частное предприятие",
  ltd: "ООО",
  jsc: "АО",
  ie: "ИП",
  other: "Иная форма",
};

export function BorrowerCard({ borrower }: { borrower: DossierViewDto["borrower"] }) {
  return (
    <div className="flex h-full flex-col rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-start justify-between border-b border-[var(--border)] px-[22px] py-4">
        <div>
          <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ink-4)] uppercase">
            Карточка заёмщика
          </div>
          <h3 className="m-0 mt-1 text-[16px] font-semibold tracking-[-0.2px] text-[var(--ink-1)]">
            {borrower.name}
          </h3>
          <p className="m-0 mt-0.5 font-mono text-[12px] text-[var(--ink-3)]">
            ИНН {borrower.inn}
          </p>
        </div>

        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#BFE2D2] bg-[var(--state-ok-bg)] px-2.5 py-1 text-[11px] font-semibold text-[var(--state-ok-fg)]">
          <CheckCircle2 className="size-3.5" />
          Проверено в ГНК
        </span>
      </header>

      <dl className="grid flex-1 grid-cols-[140px_1fr] gap-x-4 gap-y-3 px-[22px] py-4 text-[13px]">
        <Row label="ОПФ" value={LEGAL_FORM_LABEL[borrower.legal_form]} />
        <Row label="Регистрация" value={formatRuDate(borrower.registration_date)} />
        <Row
          label="Директор"
          value={
            <>
              {borrower.director_name}
              <span className="ml-1 text-[var(--ink-4)]">
                · с {formatRuDate(borrower.director_appointed_at)}
              </span>
            </>
          }
        />
        <Row label="ОКВЭД" value={borrower.okved_main} />
        <Row label="Адрес" value={borrower.registered_address} />
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-[var(--ink-3)]">{label}</dt>
      <dd className="m-0 text-[var(--ink-1)]">{value}</dd>
    </>
  );
}

function formatRuDate(iso: string): string {
  const [yyyy, mm, dd] = iso.split("-");
  return `${dd}.${mm}.${yyyy}`;
}
