// Server component: gating + рендер LoginForm.
// На accountant install login не нужен — редиректим на основной экран,
// чтобы случайные ссылки на /login не показывали несущественный для режима экран.

import { redirect } from "next/navigation";
import { Suspense } from "react";

import { APP_MODE } from "@/lib/config";

import { LoginForm } from "./_components/login-form";

export const metadata = {
  title: "Вход в систему — Uzbekbank Credit",
};

export default function LoginPage() {
  if (APP_MODE !== "bank") {
    redirect("/manual-input");
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--ca-navy-900)] px-4 py-12">
      <div className="w-full max-w-[400px]">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="grid size-12 place-items-center rounded-lg border border-[#2E4470] bg-gradient-to-b from-[#2C4880] to-[#1E3360] font-mono text-[15px] font-semibold text-white">
            UB
          </div>
          <div className="text-center">
            <div className="text-[17px] font-semibold text-[#F2F4F8]">
              Uzbekbank Credit
            </div>
            <div className="mt-1 text-[11.5px] tracking-[0.5px] text-[var(--ca-muted-dark)] uppercase">
              Кредитный конвейер · v3.2
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-[#1E2D4A] bg-[#0F172A] p-7 shadow-[0_8px_24px_rgba(0,0,0,0.35)]">
          <h1 className="mb-1 text-[18px] font-semibold text-[#F2F4F8]">
            Вход в систему
          </h1>
          <p className="mb-6 text-[12.5px] text-[var(--ca-muted-dark)]">
            Используйте корпоративную учётную запись банка
          </p>
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </div>

        <p className="mt-6 text-center text-[11px] text-[var(--ca-muted-dark-2)]">
          Доступ только для авторизованных аналитиков. Все действия фиксируются в журнале аудита.
        </p>
      </div>
    </div>
  );
}
