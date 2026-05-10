// Mode-aware shell: 260px sidebar + main column. Выбирает Sidebar по
// `NEXT_PUBLIC_APP_MODE` — на одной инсталляции активен один режим
// (см. PROJECT_BRIEF Section 2).
//
// Используется shared-страницами вроде `/dossier/[id]`, к которым обращаются
// оба режима — extracting sidebar логика из дублирующихся route-group layouts.

import { type ReactNode } from "react";

import { BankSidebar } from "@/app/(bank)/_components/sidebar";
import { Sidebar as AccountantSidebar } from "@/app/(accountant)/_components/sidebar";
import { APP_MODE } from "@/lib/config";

export function AppShell({ children }: { children: ReactNode }) {
  const SidebarComponent = APP_MODE === "bank" ? BankSidebar : AccountantSidebar;
  return (
    <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)] bg-[var(--ca-bg)]">
      <SidebarComponent />
      <main className="flex min-w-0 flex-col">{children}</main>
    </div>
  );
}
