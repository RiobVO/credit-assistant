"use client";

import {
  AlertTriangle,
  BookOpen,
  ChevronDown,
  Mail,
  MessageCircle,
  Phone,
} from "lucide-react";
import { useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { cn } from "@/lib/utils";

type FaqItem = {
  id: string;
  question: string;
  answer: React.ReactNode;
};

const FAQ: FaqItem[] = [
  {
    id: "scoring",
    question: "Что означает «scoring» и как его читать?",
    answer: (
      <>
        Scoring — числовая оценка кредитного риска заёмщика от 0 до 100.
        Чем выше — тем ниже риск. Шкала разделена на три полосы:{" "}
        <b style={{ color: "var(--state-ok-fg)" }}>≥70 «к выдаче»</b>,{" "}
        <b style={{ color: "var(--state-warn-fg)" }}>40–69 «на проверку»</b>,{" "}
        <b style={{ color: "var(--state-bad-fg)" }}>&lt;40 «отклонить»</b>. Цифра —
        результат правил из YAML-реестра, не black-box ML, у каждого правила
        указан источник (ЦБ РУз, Базель III, методика банка).
      </>
    ),
  },
  {
    id: "red-flags",
    question: "Что такое «red flag» и насколько критично?",
    answer: (
      <>
        Red flag — сработавшее правило с явным негативом. Сейчас в системе
        19 правил, разделённых по severity: <b>critical</b> (требует ручной
        проверки до решения), <b>high</b> (снижает scoring сильно), <b>medium</b>
        (заметное снижение). Каждый flag сопровождается evidence — конкретные
        цифры из отчётности заёмщика. Critical-flag — повод связаться с клиентом.
      </>
    ),
  },
  {
    id: "insufficient-data",
    question: "Статус «INSUFFICIENT_DATA» — что делать?",
    answer: (
      <>
        Система не получила достаточно данных для расчёта рекомендации. Чаще
        всего это значит: нет годовых отчётов за 2 последних периода, или нет
        VAT-периодов из Soliq. Откройте досье — раздел «Готовность данных»
        покажет, чего не хватает. Догрузите файлы через «Пересобрать с
        дополнениями».
      </>
    ),
  },
  {
    id: "xltx",
    question: "Как импортировать выгрузки Soliq (.xltx)?",
    answer: (
      <>
        Поддерживается 5 форматов из my3.soliq.uz: VAT decl., Ilova приложение №4
        (продажи), Form 2 (Отчёт о финансовых результатах), Form 1 (Баланс),
        Profit Tax. Drag-n-drop в Шаге 2 мастера «Новая заявка». Парсер
        best-effort: упадёт только на неизвестный формат, частичные ошибки
        ячеек — warning в карточке файла.
      </>
    ),
  },
  {
    id: "rebuild",
    question: "Что делает «Пересобрать с дополнениями»?",
    answer: (
      <>
        Открывает мастер «Новая заявка» с pre-fill borrower-данных из текущего
        досье. Финансовые поля и кредит остаются пустыми — заполняются с нуля.
        Полезно когда пришёл свежий FORM_2 или новая Ilova и нужно обновить
        scoring.
      </>
    ),
  },
  {
    id: "audit",
    question: "Где найти журнал действий аналитика?",
    answer: (
      <>
        Все ключевые действия (login, search, view, generate, download) пишутся
        в audit log с маскированным ИНН. Доступ к журналу — у руководителя
        управления и compliance-офицера через админ-консоль. Аналитик свой лог
        видит в разделе «Профиль» (в разработке).
      </>
    ),
  },
  {
    id: "support",
    question: "Куда писать при ошибке системы?",
    answer: (
      <>
        Если экран показывает ошибку или скоринг выглядит подозрительно — пишите
        в чат поддержки <code>#credit-assistant</code> в корпоративном Slack или
        на ops@uzbekbank.uz. Приложите ИНН досье и скриншот. Команда отвечает в
        течение рабочего дня.
      </>
    ),
  },
];

export function HelpView() {
  return (
    <>
      <BankPageHead
        title="Помощь"
        subtitle="Часто задаваемые вопросы и контакты команды поддержки Credit Assistant."
      />

      <div className="grid gap-6 md:grid-cols-[1fr_300px]">
        <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
          <header className="border-b border-[var(--border)] px-6 py-4">
            <h2 className="m-0 text-[16px] font-semibold tracking-[-0.01em] text-[var(--ink-1)]">
              Частые вопросы
            </h2>
          </header>
          <div className="divide-y divide-[var(--border)]">
            {FAQ.map((item) => (
              <FaqRow key={item.id} item={item} />
            ))}
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <ContactCard
            icon={<Mail className="size-4" />}
            title="Email поддержки"
            value="ops@uzbekbank.uz"
            href="mailto:ops@uzbekbank.uz"
          />
          <ContactCard
            icon={<MessageCircle className="size-4" />}
            title="Чат Slack"
            value="#credit-assistant"
            hint="внутренний корпоративный Slack"
          />
          <ContactCard
            icon={<Phone className="size-4" />}
            title="Hotline"
            value="+998 71 200-00-00"
            hint="будни 09:00–18:00 Ташкент"
          />
          <ContactCard
            icon={<BookOpen className="size-4" />}
            title="Документация"
            value="docs.credit-assistant"
            hint="методология scoring и список правил"
          />
          <div className="rounded-lg border border-[#F1D9A6] bg-[#FFF6E5] p-4 text-[13px] text-[var(--state-warn-fg)]">
            <div className="mb-1 inline-flex items-center gap-1.5 font-semibold">
              <AlertTriangle className="size-3.5" />
              Срочные инциденты
            </div>
            <div className="text-[12.5px] leading-[1.45]">
              Если данные клиента стали видны другому аналитику — немедленно
              позвоните в compliance.
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}

function FaqRow({ item }: { item: FaqItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left text-[14px] font-medium text-[var(--ink-1)] transition-colors hover:bg-[var(--surface-2)]"
      >
        {item.question}
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-[var(--ink-3)] transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <div className="px-6 pb-5 text-[13.5px] leading-[1.55] text-[var(--ink-2)]">
          {item.answer}
        </div>
      ) : null}
    </div>
  );
}

function ContactCard({
  icon,
  title,
  value,
  href,
  hint,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  href?: string;
  hint?: string;
}) {
  const inner = (
    <>
      <div className="mb-2 inline-flex items-center gap-2 text-[12px] font-medium text-[var(--ink-3)]">
        <span className="text-[var(--brand-primary)]">{icon}</span>
        {title}
      </div>
      <div className="text-[14px] font-semibold text-[var(--ink-1)]">{value}</div>
      {hint ? (
        <div className="mt-1 text-[12px] text-[var(--ink-3)]">{hint}</div>
      ) : null}
    </>
  );
  if (href) {
    return (
      <a
        href={href}
        className="block rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)]"
      >
        {inner}
      </a>
    );
  }
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      {inner}
    </div>
  );
}
