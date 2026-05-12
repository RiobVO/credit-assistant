import { Info, ListOrdered, Coins } from "lucide-react";
import { type ReactNode } from "react";

type Variant = "registry" | "financials" | "final";

type Content = { icon: ReactNode; text: ReactNode };

const variants: Record<Variant, Content> = {
  registry: {
    icon: <Info className="size-4" />,
    text: (
      <>
        <b className="text-[#0F2A5C]">Предзаполнение из реестра.</b> После ввода
        ИНН система автоматически подгружает наименование, ОПФ, ОКВЭД и сведения
        о директоре из реестра ГНК. Проверьте корректность всех полей.
      </>
    ),
  },
  financials: {
    icon: <ListOrdered className="size-4" />,
    text: (
      <>
        <b className="text-[#0F2A5C]">Импорт из 1С / банковских выписок.</b> Все
        суммы вводятся в сумах (UZS) без копеек. Поквартальные значения
        суммируются автоматически — итоги по году и трёхлетняя динамика
        доступны под таблицей.
      </>
    ),
  },
  final: {
    icon: <Coins className="size-4" />,
    text: (
      <>
        <b className="text-[#0F2A5C]">Финальный шаг.</b> Укажите желаемые
        параметры кредита. После отправки заявки система рассчитает
        скоринговый балл, PD/LGD и вероятность одобрения.
      </>
    ),
  },
};

export function InfoBanner({ variant }: { variant: Variant }) {
  const { icon, text } = variants[variant];
  return (
    <div className="mb-[22px] flex items-start gap-3 rounded-lg border border-[#D4E1F7] bg-[#F4F8FF] px-[14px] py-3">
      <span className="mt-px flex-none text-[var(--brand-primary)]">
        {icon}
      </span>
      <div className="text-[13px] leading-[1.5] text-[#1A3A78]">{text}</div>
    </div>
  );
}
