import { type ReactNode } from "react";

import { BankSidebar } from "@/app/(bank)/_components/sidebar";
import { BankTopbar } from "@/app/(bank)/_components/topbar";
import { Sidebar as AccountantSidebar } from "@/app/(accountant)/_components/sidebar";
import { APP_MODE } from "@/lib/config";

// Shared dossier-layout: используется обоими режимами через `/dossier/[id]`.
// Server component → APP_MODE напрямую (useAppMode hook применяется
// только в client components, см. ADR-0011 + CA-061).
export default function DossierLayout({ children }: { children: ReactNode }) {
  const isBank = APP_MODE === "bank";
  const SidebarComponent = isBank ? BankSidebar : AccountantSidebar;
  return (
    <div className="grid min-h-screen grid-cols-[248px_minmax(0,1fr)] bg-[var(--surface-2)]">
      <SidebarComponent />
      <div className="flex min-w-0 flex-col bg-[var(--surface)]">
        {isBank ? <BankTopbar /> : null}
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
