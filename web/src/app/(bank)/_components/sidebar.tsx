"use client";

import { HelpCircle, History as HistoryIcon, LogOut, Plus, Search, Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode } from "react";

import { useAnalyst, useLogout } from "@/lib/auth";
import { useBrand } from "@/lib/brand-context";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  count?: number | null;
};

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 rounded-md px-[10px] py-2 text-[13.5px] font-medium transition-colors",
        active
          ? "bg-white text-[var(--nav-text)] font-semibold shadow-[inset_2px_0_0_var(--brand-primary),0_1px_0_rgba(14,21,37,0.04)]"
          : "text-[var(--nav-text-2)] hover:bg-[var(--nav-bg-hover)] hover:text-[var(--nav-text)]",
      )}
    >
      <span className="flex shrink-0 items-center">{item.icon}</span>
      <span className="truncate">{item.label}</span>
      {item.count != null ? (
        <span className="ml-auto rounded-full bg-[var(--surface-3)] px-[6px] py-px text-[11px] font-medium text-[var(--nav-text-2)]">
          {item.count}
        </span>
      ) : null}
    </Link>
  );
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const second = parts[1]?.[0] ?? "";
  return (first + second).toUpperCase() || "??";
}

function useRoleLabel() {
  const t = useTranslations("bank.sidebar");
  return (role: string | undefined): string => {
    if (role === "senior_analyst") return t("role_senior");
    if (role === "analyst") return t("role_analyst");
    return role ?? "";
  };
}

export function BankSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: analyst } = useAnalyst();
  const logout = useLogout();
  const tNav = useTranslations("shared.nav");
  const tSidebar = useTranslations("bank.sidebar");
  const tCta = useTranslations("bank.cta");
  const roleLabel = useRoleLabel();
  const brand = useBrand();

  const PRIMARY: NavItem[] = [
    { href: "/search", label: tNav("search"), icon: <Search className="size-[17px]" /> },
    { href: "/history", label: tNav("history"), icon: <HistoryIcon className="size-[17px]" /> },
  ];
  const SECONDARY: NavItem[] = [
    { href: "/help", label: tNav("help"), icon: <HelpCircle className="size-[17px]" /> },
    { href: "/settings", label: tNav("settings"), icon: <Settings className="size-[17px]" /> },
  ];

  const handleLogout = async () => {
    await logout.mutateAsync();
    router.push("/login");
    router.refresh();
  };

  return (
    <aside className="sticky top-0 flex h-screen flex-col border-r border-[var(--nav-border)] bg-[var(--nav-bg)] text-[var(--nav-text)]">
      {/* Brand */}
      <div className="flex items-center gap-[10px] border-b border-[var(--nav-border)] px-5 pt-[18px] pb-4">
        <div className="grid size-7 shrink-0 place-items-center rounded-md bg-gradient-to-br from-[var(--brand-primary)] to-[var(--brand-primary-hover)] text-[13px] font-bold tracking-[-0.02em] text-white shadow-[0_1px_0_rgba(255,255,255,0.4)_inset,0_4px_10px_-4px_color-mix(in_oklab,var(--brand-primary)_55%,transparent)]">
          {brand.logoMark}
        </div>
        <div className="min-w-0">
          <div className="truncate text-[14px] font-semibold tracking-[-0.01em] text-[var(--nav-text)]">
            {brand.name}
          </div>
          <div className="mt-0.5 truncate text-[11px] tracking-[0.02em] text-[var(--nav-text-3)]">
            {brand.tagline}
          </div>
        </div>
      </div>

      {/* Premium card CTA «+ Новая заявка» — Phase 2 DS-PHASE-2 pattern.
          Белая карточка с brand-soft icon-tile + rotating plus на hover.
          Pattern: Linear / Notion / Mercury «Create new». */}
      <div className="px-3 pt-4">
        <Link
          href="/manual-input"
          className="group flex items-center gap-[10px] rounded-[10px] border border-[color-mix(in_oklab,var(--ink-1)_7%,transparent)] bg-white px-[9px] py-[9px] text-[var(--ink-1)] shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_1px_2px_rgba(14,21,37,0.02),0_6px_14px_-10px_rgba(14,21,37,0.12)] transition-all duration-200 ease-out hover:-translate-y-px hover:border-[var(--brand-primary)] hover:shadow-[0_1px_0_rgba(255,255,255,0.7)_inset,0_1px_2px_rgba(14,21,37,0.02),0_12px_22px_-10px_color-mix(in_oklab,var(--brand-primary)_50%,transparent)]"
        >
          <span
            className="grid size-[26px] shrink-0 place-items-center rounded-[7px] border text-[var(--brand-primary)] transition-transform duration-220 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:rotate-90"
            style={{
              background: "var(--brand-primary-soft)",
              borderColor: "color-mix(in oklab, var(--brand-primary) 18%, transparent)",
            }}
          >
            <Plus className="size-[14px]" strokeWidth={2.6} />
          </span>
          <span className="flex-1 text-[12.5px] font-semibold tracking-[-0.005em]">
            {tCta("new_application")}
          </span>
        </Link>
      </div>

      {/* Primary nav — workspace */}
      <div className="px-3 pt-5 pb-2">
        <div className="px-3 pb-2 text-[10.5px] font-semibold tracking-[0.1em] text-[var(--nav-text-3)] uppercase">
          {tSidebar("workspace")}
        </div>
        <nav className="flex flex-col gap-px">
          {PRIMARY.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
            />
          ))}
        </nav>
      </div>

      {/* Secondary nav — help (внизу) */}
      <div className="mt-auto px-3 pb-2">
        <div className="px-3 pb-2 text-[10.5px] font-semibold tracking-[0.1em] text-[var(--nav-text-3)] uppercase">
          {tSidebar("help_section")}
        </div>
        <nav className="flex flex-col gap-px">
          {SECONDARY.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
            />
          ))}
        </nav>
      </div>

      {/* User card — gradient bg + online-dot + role · онлайн */}
      <div className="m-3 mt-1 flex items-center gap-3 rounded-[10px] border border-[color-mix(in_oklab,var(--ink-1)_6%,transparent)] bg-gradient-to-b from-white/60 to-white/30 p-[10px]">
        <div className="relative">
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[var(--brand-primary-soft)] to-[color-mix(in_oklab,var(--brand-primary)_25%,white)] text-[12px] font-semibold text-[var(--brand-primary-ink)]">
            {analyst ? initials(analyst.full_name) : "—"}
          </div>
          {/* Online dot: pulse-ring-ok keyframe. border 2px = bg cream поверх state-ok. */}
          <span
            aria-hidden
            className="pulse-ring-ok absolute -right-[1px] -bottom-[1px] size-[10px] rounded-full border-2 border-[var(--nav-bg)]"
            style={{ background: "var(--state-ok-fg)" }}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[12.5px] leading-tight font-semibold text-[var(--nav-text)]">
            {analyst?.full_name ?? "—"}
          </div>
          <div className="mt-0.5 truncate text-[10.5px] text-[var(--nav-text-3)]">
            {roleLabel(analyst?.role)} · {tSidebar("online")}
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={logout.isPending}
          aria-label={tSidebar("logout_aria")}
          title={tSidebar("logout_aria")}
          className="grid size-7 shrink-0 place-items-center rounded text-[var(--nav-text-3)] transition-colors hover:bg-[var(--nav-bg-hover)] hover:text-[var(--nav-text)] disabled:cursor-wait disabled:opacity-60"
        >
          <LogOut className="size-4" />
        </button>
      </div>
    </aside>
  );
}
