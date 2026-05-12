import Link from "next/link";

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          Страница не найдена
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          Возможно, она была перемещена или удалена.
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          На главную
        </Link>
      </div>
    </div>
  );
}
