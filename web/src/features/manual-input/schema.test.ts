// CA-038: валидация юр.адреса — ≥15 символов и цифра (номер дома).
import { describe, it, expect } from "vitest";

import { step1Schema } from "./schema";

const baseStep1 = {
  inn: "201308534",
  name: "ООО Тест",
  legalForm: "llc" as const,
  registrationDate: "2020-01-01",
  okedMain: "62.01",
  directorName: "Иванов И.И.",
  directorAppointedAt: "2020-01-01",
  registeredAddress: "г. Ташкент, ул. Амира Темура, 12",
  // ADR-0024 Session 3: новые поля schema (boolean toggle + read-only date).
  okedChangedByOwner: false,
  okedMainChangedAt: null,
};

describe("step1Schema.registeredAddress (CA-038)", () => {
  it("принимает полный адрес с улицей и номером дома", () => {
    expect(step1Schema.safeParse(baseStep1).success).toBe(true);
  });

  it("отклоняет «Ташкент» — короче 15 символов", () => {
    const res = step1Schema.safeParse({ ...baseStep1, registeredAddress: "Ташкент" });
    expect(res.success).toBe(false);
    if (!res.success) {
      const msg = res.error.issues.find((i) => i.path[0] === "registeredAddress")?.message;
      expect(msg).toMatch(/15 символов/);
    }
  });

  it("отклоняет адрес ≥15 символов, но без цифр", () => {
    const res = step1Schema.safeParse({
      ...baseStep1,
      registeredAddress: "город Ташкент улица Амира Темура",
    });
    expect(res.success).toBe(false);
    if (!res.success) {
      const msg = res.error.issues.find((i) => i.path[0] === "registeredAddress")?.message;
      expect(msg).toMatch(/номер дома/);
    }
  });

  it("принимает ровно 15 символов с цифрой", () => {
    const res = step1Schema.safeParse({
      ...baseStep1,
      registeredAddress: "Ташкент, дом 12",
    });
    expect(res.success).toBe(true);
  });
});
