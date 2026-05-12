import { getTranslations } from "next-intl/server";
import Link from "next/link";

export default async function NotFound() {
  const t = await getTranslations("shared.states");
  const tCta = await getTranslations("shared.cta");
  return (
    <div className="grid min-h-screen place-items-center bg-[var(--bg)] p-6">
      <div className="max-w-md rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h1 className="text-[18px] font-semibold text-[var(--ink-1)]">
          {t("not_found")}
        </h1>
        <p className="mt-2 text-[13.5px] text-[var(--ink-3)]">
          {t("not_found_hint")}
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-md bg-[var(--brand-primary)] px-4 py-2 text-[13.5px] font-semibold text-white hover:bg-[var(--brand-primary-hover)]"
        >
          {tCta("go_home")}
        </Link>
      </div>
    </div>
  );
}
