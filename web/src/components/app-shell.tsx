"use client";

// Mode-aware shell: 260px sidebar + main column + GlobalTopbar + ⌘K палитра.
// Sidebar выбирается по APP_MODE — на одной инсталляции активен один режим
// (см. PROJECT_BRIEF Section 2, ADR-0011).
//
// Manual-input использует собственный Topbar (внутри view) → showTopbar={false}.

import { usePathname } from "next/navigation";
import { type ReactNode, useState } from "react";

import { BankSidebar } from "@/app/(bank)/_components/sidebar";
import { Sidebar as AccountantSidebar } from "@/app/(accountant)/_components/sidebar";
import { CommandPalette } from "@/components/command-palette";
import { GlobalTopbar, type Crumb } from "@/components/global-topbar";
import { useAppMode } from "@/lib/use-app-mode";

function deriveCrumbs(pathname: string): Crumb[] {
  if (pathname.startsWith("/search")) return [{ label: "Поиск заёмщика", current: true }];
  if (pathname.startsWith("/history")) return [{ label: "История досье", current: true }];
  if (pathname.startsWith("/dossier/")) {
    return [
      { label: "История", href: "/history" },
      { label: "Досье", current: true },
    ];
  }
  if (pathname.startsWith("/settings")) return [{ label: "Настройки", current: true }];
  if (pathname.startsWith("/help")) return [{ label: "Помощь", current: true }];
  return [];
}

export function AppShell({
  children,
  showTopbar = true,
}: {
  children: ReactNode;
  showTopbar?: boolean;
}) {
  const mode = useAppMode();
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const SidebarComponent = mode === "bank" ? BankSidebar : AccountantSidebar;
  const crumbs = deriveCrumbs(pathname);

  return (
    <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)] bg-[var(--bg)]">
      <SidebarComponent />
      <main className="flex min-w-0 flex-col">
        {showTopbar && (
          <GlobalTopbar
            crumbs={crumbs}
            onSearchOpen={() => setPaletteOpen(true)}
          />
        )}
        <div className="flex-1">{children}</div>
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      </main>
    </div>
  );
}
