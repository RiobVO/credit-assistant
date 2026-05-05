// Возвращает {key, values} для подстановки в next-intl t() — null если дата
// старше 7 дней (для них relative time не показываем, остаётся абсолютная).
// «Вчера» — календарный yesterday (а не «24-48 часов назад»), чтобы строка
// 02:00 сегодняшнего дня и 23:00 вчерашнего показывали правильно.

export type RelativeTimeMessage =
  | { key: "rel_just_now" }
  | { key: "rel_minutes"; values: { n: number } }
  | { key: "rel_hours"; values: { n: number } }
  | { key: "rel_yesterday"; values: { time: string } }
  | { key: "rel_days"; values: { n: number } };

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function formatRelativeTime(
  iso: string,
  now: Date = new Date(),
): RelativeTimeMessage | null {
  const d = new Date(iso);
  const diffSec = (now.getTime() - d.getTime()) / 1000;
  if (diffSec < 0) return null;
  if (diffSec < 60) return { key: "rel_just_now" };

  const sameDay =
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear();

  if (sameDay) {
    if (diffSec < 3600) {
      return { key: "rel_minutes", values: { n: Math.floor(diffSec / 60) } };
    }
    return { key: "rel_hours", values: { n: Math.floor(diffSec / 3600) } };
  }

  const dayDiff = Math.round(
    (startOfDay(now).getTime() - startOfDay(d).getTime()) / 86_400_000,
  );

  if (dayDiff === 1) {
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return { key: "rel_yesterday", values: { time: `${hh}:${mm}` } };
  }
  if (dayDiff >= 2 && dayDiff < 7) {
    return { key: "rel_days", values: { n: dayDiff } };
  }
  return null;
}

// Свежая запись (сегодня или вчера) — рендерим relative подкрашенной зелёным.
export function isFreshTime(iso: string, now: Date = new Date()): boolean {
  const d = new Date(iso);
  const diffSec = (now.getTime() - d.getTime()) / 1000;
  if (diffSec < 0 || diffSec >= 86_400 * 2) return false;
  const dayDiff = Math.round(
    (startOfDay(now).getTime() - startOfDay(d).getTime()) / 86_400_000,
  );
  return dayDiff <= 1;
}
