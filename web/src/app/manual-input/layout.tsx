import { type ReactNode } from "react";

import { AppShell } from "@/components/app-shell";

export default function ManualInputLayout({ children }: { children: ReactNode }) {
  // Manual-input использует собственный Topbar внутри view → отключаем
  // GlobalTopbar чтобы breadcrumbs не дублировались.
  return <AppShell showTopbar={false}>{children}</AppShell>;
}
