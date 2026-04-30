import {
  LayoutDashboard,
  FileText,
  Users,
  TrendingUp,
  Briefcase,
  Plus,
  ListOrdered,
  Clock,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  badge?: string;
  active?: boolean;
};

const main: NavItem[] = [
  { href: "#", label: "Панель управления", icon: <LayoutDashboard className="size-4" /> },
  {
    href: "/manual-input",
    label: "Заявки на кредит",
    icon: <FileText className="size-4" />,
    badge: "24",
    active: true,
  },
  { href: "#", label: "Заёмщики", icon: <Users className="size-4" /> },
  { href: "#", label: "Скоринг и аналитика", icon: <TrendingUp className="size-4" /> },
  { href: "#", label: "Портфель", icon: <Briefcase className="size-4" /> },
];

const tools: NavItem[] = [
  { href: "#", label: "Новый анализ", icon: <Plus className="size-4" /> },
  { href: "#", label: "Отчёты", icon: <ListOrdered className="size-4" /> },
  { href: "#", label: "История", icon: <Clock className="size-4" /> },
  { href: "#", label: "Настройки", icon: <Settings className="size-4" /> },
];

function NavLink({ item }: { item: NavItem }) {
  return (
    <Link
      href={item.href}
      aria-current={item.active ? "page" : undefined}
      className={cn(
        "group/navlink flex items-center gap-3 rounded-md px-3 py-[9px] text-[13.5px] font-medium transition-colors",
        item.active
          ? "bg-[var(--nav-bg-hover)] text-white shadow-[inset_2px_0_0_#4A7BD9]"
          : "text-[#C5CCDA] hover:bg-[var(--nav-bg-2)] hover:text-white",
      )}
    >
      <span
        className={cn(
          "flex size-4 items-center justify-center transition-colors",
          item.active ? "text-[#A9C2F1]" : "text-[#9AA6BC]",
        )}
      >
        {item.icon}
      </span>
      <span className="truncate">{item.label}</span>
      {item.badge ? (
        <span
          className={cn(
            "ml-auto rounded-full px-[7px] py-px text-[11px] font-medium",
            item.active
              ? "bg-[#274476] text-[#D8E5FB]"
              : "bg-[#243049] text-[#B7C2D8]",
          )}
        >
          {item.badge}
        </span>
      ) : null}
    </Link>
  );
}

function NavSection({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div className="px-3 pt-4 pb-1">
      <div className="px-[10px] pb-2 text-[10.5px] font-medium tracking-[1.2px] text-[var(--nav-text-3)] uppercase">
        {title}
      </div>
      <nav className="flex flex-col gap-px px-2">
        {items.map((it) => (
          <NavLink key={it.label} item={it} />
        ))}
      </nav>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="flex h-screen sticky top-0 flex-col border-r border-black bg-[var(--nav-bg)] text-[#E6EAF2]">
      <div className="flex items-center gap-[10px] border-b border-[var(--nav-border)] px-5 pt-5 pb-[22px]">
        <div className="grid size-8 place-items-center rounded-md border border-[#2E4470] bg-gradient-to-b from-[#2C4880] to-[#1E3360] font-mono text-[13px] font-semibold text-white">
          CR
        </div>
        <div>
          <div className="text-sm font-semibold tracking-[0.2px] text-[#F2F4F8]">
            CreditScope
          </div>
          <div className="mt-0.5 text-[11px] tracking-[0.5px] text-[var(--nav-text-2)] uppercase">
            Risk Suite · v3.2
          </div>
        </div>
      </div>

      <NavSection title="Основное" items={main} />
      <NavSection title="Инструменты" items={tools} />

      <div className="mt-auto flex items-center gap-[10px] border-t border-[var(--nav-border)] px-[14px] py-[14px] pb-[18px]">
        <div className="grid size-[34px] place-items-center rounded-full border border-[#324567] bg-[var(--nav-bg-hover)] text-xs font-semibold text-[#D8E0EE]">
          ИК
        </div>
        <div>
          <div className="text-[13px] font-medium text-[#E6EAF2]">И. Каримов</div>
          <div className="text-[11px] text-[var(--nav-text-2)]">
            Кредитный аналитик
          </div>
        </div>
      </div>
    </aside>
  );
}
