// Inline-helper для Шага 1 manual-input: подсчитывает срок (deference в
// годах + остаточных месяцах) от `from` до `now`, форматирует в RU plural.
// Pure — `now` инжектируется для детерминированных тестов.

export function formatBusinessAge(
  from: string | undefined,
  now: Date = new Date(),
): string | null {
  if (!from || !/^\d{4}-\d{2}-\d{2}$/.test(from)) return null;
  const reg = new Date(from);
  if (Number.isNaN(reg.getTime())) return null;
  if (reg > now) return null;

  let years = now.getFullYear() - reg.getFullYear();
  let months = now.getMonth() - reg.getMonth();
  if (now.getDate() < reg.getDate()) months -= 1;
  if (months < 0) {
    years -= 1;
    months += 12;
  }

  if (years === 0) return pluralMonths(months);
  if (months === 0) return pluralYears(years);
  return `${pluralYears(years)} ${pluralMonths(months)}`;
}

function pluralYears(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return `${n} лет`;
  if (mod10 === 1) return `${n} год`;
  if (mod10 >= 2 && mod10 <= 4) return `${n} года`;
  return `${n} лет`;
}

function pluralMonths(n: number): string {
  return `${n} мес.`;
}
