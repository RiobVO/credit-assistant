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
        "flex items-center gap-3 rounded-md px-[10px] py-2 text-[14px] font-medium transition-colors",
        active
          ? "bg-[var(--nav-bg-hover)] text-white"
          : "text-[var(--nav-text-2)] hover:bg-[var(--nav-bg-hover)] hover:text-[var(--nav-text)]",
      )}
    >
      <span className="flex shrink-0 items-center">{item.icon}</span>
      <span className="truncate">{item.label}</span>
      {item.count != null ? (
        <span className="ml-auto rounded-full bg-white/[0.08] px-[6px] py-px text-[11px] font-medium text-[var(--nav-text-2)]">
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
        <div className="grid size-7 shrink-0 place-items-center rounded-md bg-gradient-to-br from-[var(--brand-primary)] to-[var(--brand-primary-hover)] text-[13px] font-bold tracking-[-0.02em] text-white">
          {brand.logoMark}
        </div>
        <div className="min-w-0">
          <div className="truncate text-[14px] font-semibold tracking-[-0.01em] text-white">
            {brand.name}
          </div>
          <div className="mt-0.5 text-[11px] tracking-[0.02em] text-[var(--nav-text-3)]">
            {brand.tagline}
          </div>
        </div>
      </div>

      {/* CTA «+ Новая заявка» — terracotta accent (CA-051 sustained). */}
      <div className="px-3 pt-4">
        <Link
          href="/manual-input"
          className="flex items-center justify-center gap-2 rounded-md bg-[var(--brand-primary)] px-3 py-[10px] text-[13.5px] font-semibold text-white shadow-sm transition-colors hover:bg-[var(--brand-primary-hover)]"
        >
          <Plus className="size-4" />
          {tCta("new_application")}
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

      {/* User card */}
      <div className="flex items-center gap-3 border-t border-[var(--nav-border)] p-4">
        <div className="grid size-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[var(--brand-primary)] to-[var(--brand-primary-hover)] text-[12px] font-semibold text-white">
          {analyst ? initials(analyst.full_name) : "—"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium leading-tight text-white">
            {analyst?.full_name ?? "—"}
          </div>
          <div className="mt-0.5 truncate text-[11px] text-[var(--nav-text-3)]">
            {roleLabel(analyst?.role)}
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
