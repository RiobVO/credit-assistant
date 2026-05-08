import { type ReactNode } from "react";

import { Sidebar } from "./_components/sidebar";

export default function AccountantLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)] bg-[var(--ca-bg)]">
      <Sidebar />
      <main className="flex min-w-0 flex-col">{children}</main>
    </div>
  );
}
