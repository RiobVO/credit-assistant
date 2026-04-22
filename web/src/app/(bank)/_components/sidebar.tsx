"use client";

import { Clock, LogOut, Search } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode } from "react";

import { useAnalyst, useLogout } from "@/lib/auth";
import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: ReactNode };

const NAV: NavItem[] = [
  { href: "/search", label: "Поиск заёмщика", icon: <Search className="size-4" /> },
  { href: "/history", label: "История досье", icon: <Clock className="size-4" /> },
];

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-md px-3 py-[9px] text-[13.5px] font-medium transition-colors",
        active
          ? "bg-[var(--ca-navy-600)] text-white shadow-[inset_2px_0_0_#4A7BD9]"
          : "text-[#C5CCDA] hover:bg-[var(--ca-navy-700)] hover:text-white",
      )}
    >
      <span
        className={cn(
          "flex size-4 items-center justify-center transition-colors",
          active ? "text-[#A9C2F1]" : "text-[#9AA6BC]",
        )}
      >
        {item.icon}
      </span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const second = parts[1]?.[0] ?? "";
  return (first + second).toUpperCase() || "??";
}

export function BankSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: analyst } = useAnalyst();
  const logout = useLogout();

  const handleLogout = async () => {
    await logout.mutateAsync();
    router.push("/login");
    router.refresh();
  };

  return (
    <aside className="sticky top-0 flex h-screen flex-col border-r border-black bg-[var(--ca-navy-900)] text-[#E6EAF2]">
      <div className="flex items-center gap-[10px] border-b border-[var(--ca-line-dark)] px-5 pt-5 pb-[22px]">
        <div className="grid size-8 place-items-center rounded-md border border-[#2E4470] bg-gradient-to-b from-[#2C4880] to-[#1E3360] font-mono text-[13px] font-semibold text-white">
          UB
        </div>
        <div>
          <div className="text-sm font-semibold tracking-[0.2px] text-[#F2F4F8]">
            Uzbekbank Credit
          </div>
          <div className="mt-0.5 text-[11px] tracking-[0.5px] text-[var(--ca-muted-dark)] uppercase">
            Кредитный конвейер
          </div>
        </div>
      </div>

      <div className="px-3 pt-4 pb-1">
        <div className="px-[10px] pb-2 text-[10.5px] font-medium tracking-[1.2px] text-[var(--ca-muted-dark-2)] uppercase">
          Анализ заявок
        </div>
        <nav className="flex flex-col gap-px px-2">
          {NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
            />
          ))}
        </nav>
      </div>

      <div className="mt-auto border-t border-[var(--ca-line-dark)]">
        <div className="flex items-center gap-[10px] px-[14px] py-[14px]">
          <div className="grid size-[34px] place-items-center rounded-full border border-[#324567] bg-[var(--ca-navy-500)] text-xs font-semibold text-[#D8E0EE]">
            {analyst ? initials(analyst.full_name) : "—"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-medium text-[#E6EAF2]">
              {analyst?.full_name ?? "—"}
            </div>
            <div className="truncate text-[11px] text-[var(--ca-muted-dark)]">
              {analyst?.role === "senior_analyst"
                ? "Старший аналитик"
                : analyst?.role === "analyst"
                  ? "Кредитный аналитик"
                  : (analyst?.role ?? "")}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={logout.isPending}
          className="flex w-full items-center gap-2 border-t border-[var(--ca-line-dark)] px-[14px] py-[12px] text-left text-[12.5px] text-[#C5CCDA] transition-colors hover:bg-[var(--ca-navy-700)] hover:text-white disabled:cursor-wait disabled:opacity-60"
        >
          <LogOut className="size-4 text-[#9AA6BC]" />
          {logout.isPending ? "Выходим…" : "Выйти"}
        </button>
      </div>
    </aside>
  );
}
