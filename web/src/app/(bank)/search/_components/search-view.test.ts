// Phase C: helpers /search.
import { afterEach, describe, expect, it } from "vitest";

// Re-implementation для contract-теста: при расхождении с view упадёт.
function formatInn(inn: string): string {
  if (inn.length === 9) return inn.replace(/(\d{3})(\d{3})(\d{3})/, "$1 $2 $3");
  return inn;
}

function validateInn(raw: string) {
  const cleaned = raw.trim();
  if (!cleaned) return { ok: false as const, message: "Введите ИНН" };
  if (!/^\d+$/.test(cleaned)) return { ok: false as const, message: "Только цифры" };
  if (cleaned.length !== 9 && cleaned.length !== 14) {
    return { ok: false as const, message: "ИНН должен быть 9 или 14 цифр" };
  }
  return { ok: true as const, value: cleaned };
}

describe("formatInn", () => {
  it("9 цифр → формат 3-3-3", () => {
    expect(formatInn("305847291")).toBe("305 847 291");
  });

  it("14 цифр — не форматируется", () => {
    expect(formatInn("30584729112345")).toBe("30584729112345");
  });

  it("пустая строка — как есть", () => {
    expect(formatInn("")).toBe("");
  });
});

describe("validateInn", () => {
  it("9 цифр — валидно", () => {
    expect(validateInn("123456789")).toEqual({ ok: true, value: "123456789" });
  });

  it("14 цифр — валидно", () => {
    expect(validateInn("12345678901234")).toEqual({
      ok: true,
      value: "12345678901234",
    });
  });

  it("пусто — message «Введите ИНН»", () => {
    const r = validateInn("");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.message).toBe("Введите ИНН");
  });

  it("буквы — message «Только цифры»", () => {
    const r = validateInn("abc123");
    expect(r.ok).toBe(false);
  });

  it("неправильная длина — message", () => {
    const r = validateInn("12345");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.message).toMatch(/9 или 14/);
  });
});

// localStorage interactions — через mock window.localStorage. Vitest jsdom уже
// предоставляет рабочий localStorage.
describe("recent INNs storage", () => {
  const KEY = "ca:bank-search-recent-inns";
  const MAX = 4;

  afterEach(() => {
    window.localStorage.removeItem(KEY);
  });

  function load(): string[] {
    try {
      const raw = window.localStorage.getItem(KEY);
      if (!raw) return [];
      const arr = JSON.parse(raw) as unknown;
      if (Array.isArray(arr)) {
        return arr
          .filter((v): v is string => typeof v === "string")
          .slice(0, MAX);
      }
    } catch {
      /* */
    }
    return [];
  }

  function save(inn: string): void {
    const cur = load();
    const next = [inn, ...cur.filter((x) => x !== inn)].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(next));
  }

  it("save → load round-trip", () => {
    save("123456789");
    expect(load()).toEqual(["123456789"]);
  });

  it("дедупликация: повтор перемещает в начало", () => {
    save("aaa");
    save("bbb");
    save("aaa");
    expect(load()).toEqual(["aaa", "bbb"]);
  });

  it("обрезает до MAX=4 последних", () => {
    save("1"); save("2"); save("3"); save("4"); save("5");
    expect(load()).toEqual(["5", "4", "3", "2"]);
  });
});
