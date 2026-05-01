"use client";

import {
  Check,
  Info,
  KeyRound,
  Loader2,
  type LucideIcon,
  Monitor,
  Moon,
  Palette,
  Shield,
  Sun,
  User,
} from "lucide-react";
import { useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { useAnalyst } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Section = "profile" | "appearance" | "security" | "about";

const SECTIONS: Array<{
  key: Section;
  label: string;
  icon: LucideIcon;
}> = [
  { key: "profile", label: "Профиль", icon: User },
  { key: "appearance", label: "Внешний вид", icon: Palette },
  { key: "security", label: "Безопасность", icon: Shield },
  { key: "about", label: "О системе", icon: Info },
];

export function SettingsView() {
  const [section, setSection] = useState<Section>("profile");

  return (
    <>
      <BankPageHead
        title="Настройки"
        subtitle="Управление учётной записью аналитика и параметрами интерфейса."
      />

      <div className="grid gap-6 md:grid-cols-[220px_1fr]">
        <nav className="flex flex-col gap-1">
          {SECTIONS.map((s) => {
            const Ico = s.icon;
            const active = section === s.key;
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => setSection(s.key)}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-left text-[13.5px] font-medium transition-colors",
                  active
                    ? "bg-[var(--surface)] text-[var(--ink-1)] shadow-[0_1px_1px_rgba(15,23,42,0.04)] ring-1 ring-[var(--border)]"
                    : "text-[var(--ink-2)] hover:bg-[var(--surface)] hover:text-[var(--ink-1)]",
                )}
              >
                <Ico
                  className={cn(
                    "size-4",
                    active ? "text-[var(--brand-primary)]" : "text-[var(--ink-4)]",
                  )}
                />
                {s.label}
              </button>
            );
          })}
        </nav>

        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-7">
          {section === "profile" ? <ProfileSection /> : null}
          {section === "appearance" ? <AppearanceSection /> : null}
          {section === "security" ? <SecuritySection /> : null}
          {section === "about" ? <AboutSection /> : null}
        </div>
      </div>
    </>
  );
}

// ─────────────── Profile ───────────────

function ProfileSection() {
  const { data: analyst, isLoading } = useAnalyst();
  return (
    <SectionLayout title="Профиль аналитика" hint="Данные из учётной записи. Изменения — через администратора банка.">
      {isLoading ? (
        <div className="text-[13.5px] text-[var(--ink-3)]">Загрузка…</div>
      ) : !analyst ? (
        <div className="text-[13.5px] text-[var(--ink-3)]">
          Не удалось загрузить профиль.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <ReadField label="ФИО" value={analyst.full_name} />
          <ReadField label="Email" value={analyst.email} />
          <ReadField
            label="Роль"
            value={
              analyst.role === "senior_analyst"
                ? "Старший аналитик"
                : analyst.role === "analyst"
                  ? "Кредитный аналитик"
                  : analyst.role
            }
          />
          <ReadField label="Идентификатор" value={analyst.id} mono />
        </div>
      )}
    </SectionLayout>
  );
}

function ReadField({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-[12px] font-medium text-[var(--ink-3)]">{label}</div>
      <div
        className={cn(
          "rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[14px] text-[var(--ink-1)]",
          mono && "font-mono text-[13px] tabular-nums",
        )}
      >
        {value}
      </div>
    </div>
  );
}

// ─────────────── Appearance ───────────────

function AppearanceSection() {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("light");
  return (
    <SectionLayout title="Внешний вид" hint="Тема интерфейса. Тёмная тема скоро.">
      <div className="grid gap-3 md:grid-cols-3">
        <ThemeCard
          icon={<Sun className="size-4" />}
          label="Светлая"
          active={theme === "light"}
          onClick={() => setTheme("light")}
        />
        <ThemeCard
          icon={<Moon className="size-4" />}
          label="Тёмная"
          active={theme === "dark"}
          disabled
          hint="В разработке"
        />
        <ThemeCard
          icon={<Monitor className="size-4" />}
          label="Системная"
          active={theme === "system"}
          disabled
          hint="В разработке"
        />
      </div>
    </SectionLayout>
  );
}

function ThemeCard({
  icon,
  label,
  active,
  disabled,
  hint,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
  hint?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "relative flex flex-col items-start gap-2 rounded-md border p-4 text-left transition-colors",
        active && !disabled
          ? "border-[var(--brand-primary)] bg-[var(--brand-primary-soft)]"
          : "border-[var(--border)] bg-[var(--surface)]",
        !disabled && "hover:border-[var(--ink-4)]",
        disabled && "cursor-not-allowed opacity-55",
      )}
    >
      <span
        className={cn(
          "grid size-8 place-items-center rounded-md",
          active && !disabled
            ? "bg-[var(--brand-primary)] text-white"
            : "bg-[var(--surface-3)] text-[var(--ink-2)]",
        )}
      >
        {icon}
      </span>
      <span className="text-[13.5px] font-medium text-[var(--ink-1)]">{label}</span>
      {hint ? <span className="text-[11.5px] text-[var(--ink-3)]">{hint}</span> : null}
      {active && !disabled ? (
        <Check className="absolute top-3 right-3 size-4 text-[var(--brand-primary)]" />
      ) : null}
    </button>
  );
}

// ─────────────── Security ───────────────

function SecuritySection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [state, setState] = useState<
    | { kind: "idle" }
    | { kind: "submitting" }
    | { kind: "ok" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 12) {
      setState({ kind: "error", message: "Новый пароль — минимум 12 символов" });
      return;
    }
    if (next !== confirm) {
      setState({ kind: "error", message: "Пароли не совпадают" });
      return;
    }
    setState({ kind: "submitting" });
    try {
      // TODO: backend endpoint `/api/auth/change-password` ещё не реализован.
      // Сейчас имитируем ответ для UX-flow, как только endpoint появится —
      // подменим fetch и onError-обработку.
      await new Promise((r) => setTimeout(r, 600));
      setState({ kind: "ok" });
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Не удалось сменить пароль",
      });
    }
  };

  return (
    <SectionLayout title="Безопасность" hint="Смена пароля. Минимум 12 символов, рекомендуется менеджер паролей.">
      <form onSubmit={handleSubmit} className="grid max-w-md gap-4">
        <PasswordField
          label="Текущий пароль"
          value={current}
          onChange={setCurrent}
          autoComplete="current-password"
          required
        />
        <PasswordField
          label="Новый пароль"
          value={next}
          onChange={setNext}
          autoComplete="new-password"
          required
        />
        <PasswordField
          label="Подтвердить пароль"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
          required
        />

        {state.kind === "error" ? (
          <p role="alert" className="text-[12.5px] text-[var(--state-bad-fg)]">
            {state.message}
          </p>
        ) : null}
        {state.kind === "ok" ? (
          <p role="status" className="inline-flex items-center gap-2 text-[12.5px] text-[var(--state-ok-fg)]">
            <Check className="size-3.5" /> Пароль обновлён.
          </p>
        ) : null}

        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={state.kind === "submitting"}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--brand-primary)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {state.kind === "submitting" ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <KeyRound className="size-3.5" />
            )}
            Сменить пароль
          </button>
          <span className="text-[11.5px] text-[var(--ink-4)]">
            Endpoint в разработке — пока UI-flow без сохранения.
          </span>
        </div>
      </form>
    </SectionLayout>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[12.5px] font-medium text-[var(--ink-1)]">
        {label}
        {required ? (
          <span className="ml-1 text-[var(--brand-primary)]">*</span>
        ) : null}
      </span>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        className="h-[38px] rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-[14px] text-[var(--ink-1)] outline-none transition-colors focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]"
      />
    </label>
  );
}

// ─────────────── About ───────────────

function AboutSection() {
  const mode = process.env.NEXT_PUBLIC_APP_MODE ?? "bank";
  const buildVersion =
    process.env.NEXT_PUBLIC_BUILD_VERSION ?? "dev";
  return (
    <SectionLayout title="О системе" hint="Информация об установленной версии Credit Assistant.">
      <div className="grid gap-4 md:grid-cols-2">
        <ReadField label="Режим работы" value={mode === "bank" ? "Bank Mode" : mode} />
        <ReadField label="Версия" value={buildVersion} mono />
        <ReadField
          label="Описание"
          value="Внутренний инструмент банка для подготовки кредитного досье МСБ-заёмщика. Phase 4 Bank Mode UI."
        />
        <ReadField
          label="Поддержка"
          value="ops@uzbekbank.uz"
          mono
        />
      </div>
    </SectionLayout>
  );
}

// ─────────────── Shared layout ───────────────

function SectionLayout({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-[18px] font-semibold tracking-[-0.01em] text-[var(--ink-1)]">
          {title}
        </h2>
        {hint ? (
          <p className="m-0 text-[13px] text-[var(--ink-3)]">{hint}</p>
        ) : null}
      </div>
      {children}
    </div>
  );
}
