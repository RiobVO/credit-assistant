// Кольцевой индикатор DSCR (debt service coverage ratio).
// Заливка пропорциональна dscr / cap (по умолчанию cap = 3.0).
//
// CA-033: value === null = «недостаточно данных» → серая окружность без
// заливки, центр «—». Отличается от value=0 / value<0 (есть данные, но
// сигнал риска): там окружность градиентом, но безкольца (нечем покрывать).

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DscrGauge({
  value,
  cap = 3,
}: {
  value: number | null;
  cap?: number;
}) {
  const isProvided = value != null && Number.isFinite(value);
  const safeValue = isProvided ? Math.max(0, value) : 0;
  const fraction = Math.min(safeValue / cap, 1);
  const offset = CIRCUMFERENCE * (1 - fraction);
  // Цвет stroke: при null — серый (нейтрально). При наличии значения —
  // градиент, даже если оно <= 0 (signal «данные есть» отделён от «нет данных»).
  const strokeStyle = isProvided ? "url(#gaugeGrad)" : "#D4D9E0";

  return (
    <div className="relative size-[160px]">
      <svg viewBox="0 0 100 100" className="-rotate-90">
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0F8A5F" />
            <stop offset="100%" stopColor="#1E55C9" />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke="#EEF1F6"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke={strokeStyle}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE.toFixed(2)}
          strokeDashoffset={offset.toFixed(2)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
        <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ink-4)] uppercase">
          DSCR
        </div>
        <div className="font-mono text-[34px] leading-none font-bold tracking-[-1px] text-[var(--ink-1)]">
          {isProvided && safeValue > 0 ? formatDscrLabel(safeValue) : "—"}
          {isProvided && safeValue > 0 ? (
            <span className="ml-0.5 text-[18px] font-medium text-[var(--ink-3)]">
              ×
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// При большом долге DSCR может выйти за разумные пределы (видели 152152,00x —
// переполняет круг). Аналогично слишком маленькие значения теряют смысл.
function formatDscrLabel(value: number): string {
  if (value > 999) return ">999";
  if (value < 0.01) return "<0,01";
  return value.toFixed(2).replace(".", ",");
}
