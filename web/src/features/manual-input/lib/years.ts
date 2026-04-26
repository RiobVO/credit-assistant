// Возвращает массив из `count` лет, начиная с текущего и убывая в прошлое.
// Используется в селекторах налоговых периодов (по умолчанию — последние 15 лет).

export function getYearsRange(count: number = 15, base: number = new Date().getFullYear()): number[] {
  return Array.from({ length: count }, (_, i) => base - i);
}
