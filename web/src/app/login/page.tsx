// Server component: gating + рендер LoginView (client с spotlight).

import { redirect } from "next/navigation";
import { Suspense } from "react";

import { APP_MODE } from "@/lib/config";

import { LoginView } from "./_components/login-view";

export const metadata = {
  title: "Вход в систему — Uzbekbank Credit",
};

export default function LoginPage() {
  if (APP_MODE !== "bank") {
    redirect("/manual-input");
  }
  return (
    <Suspense fallback={null}>
      <LoginView />
    </Suspense>
  );
}
