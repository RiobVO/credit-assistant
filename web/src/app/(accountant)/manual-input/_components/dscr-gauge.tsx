// Кольцевой индикатор DSCR (debt service coverage ratio).
// Заливка пропорциональна dscr / cap (по умолчанию cap = 3.0).

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DscrGauge({
  value,
  cap = 3,
}: {
  value: number;
  cap?: number;
}) {
  const safeValue = Number.isFinite(value) ? Math.max(0, value) : 0;
  const fraction = Math.min(safeValue / cap, 1);
  const offset = CIRCUMFERENCE * (1 - fraction);

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
          stroke="url(#gaugeGrad)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE.toFixed(2)}
          strokeDashoffset={offset.toFixed(2)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
        <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-ink-400)] uppercase">
          DSCR
        </div>
        <div className="font-mono text-[34px] leading-none font-bold tracking-[-1px] text-[var(--ca-ink-900)]">
          {safeValue > 0 ? safeValue.toFixed(2).replace(".", ",") : "—"}
          {safeValue > 0 ? (
            <span className="ml-0.5 text-[18px] font-medium text-[var(--ca-ink-500)]">
              ×
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
