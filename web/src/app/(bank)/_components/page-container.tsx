import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

// Стандартный контейнер контента bank-страниц.
// Mockup: padding 32/32/56 + max-width 1240px. Применять в каждом /search,
// /history, /settings, /help. Для /dossier — может быть `wide` без max-width.
export function BankPageContainer({
  children,
  wide = false,
  className,
}: {
  children: ReactNode;
  wide?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "w-full px-8 pt-8 pb-14",
        !wide && "max-w-[1240px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
