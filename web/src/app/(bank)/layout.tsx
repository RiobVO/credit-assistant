import { type ReactNode } from "react";

import { BankSidebar } from "./_components/sidebar";
import { BankTopbar } from "./_components/topbar";

export default function BankLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-[248px_minmax(0,1fr)] bg-[var(--ub-surface-2)]">
      <BankSidebar />
      <div className="flex min-w-0 flex-col bg-[var(--ub-bg)]">
        <BankTopbar />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
