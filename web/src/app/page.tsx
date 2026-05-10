// Root redirect по режиму инсталляции. Финальный URL — не root: одна
// инсталляция = один основной флоу.

import { redirect } from "next/navigation";

import { APP_MODE } from "@/lib/config";

export default function RootPage() {
  if (APP_MODE === "bank") {
    redirect("/search");
  }
  redirect("/manual-input");
}
