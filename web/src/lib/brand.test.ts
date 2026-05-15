import { describe, it, expect } from "vitest";
import { brandSchema, loadBrandFromJson } from "./brand";

describe("brand", () => {
  it("validates a full brand config", () => {
    const raw = {
      id: "default",
      name: "Credit Assistant",
      tagline: "Accountant Mode",
      logoMark: "CA",
      primary: "#1E55C9",
      primaryHover: "#1947AA",
      primarySoft: "#EAF0FB",
      primaryInk: "#1947AA",
      primaryRing: "rgba(30,85,201,0.22)",
    };
    expect(() => brandSchema.parse(raw)).not.toThrow();
  });

  it("rejects invalid hex", () => {
    const raw = {
      id: "x",
      name: "x",
      tagline: "x",
      logoMark: "X",
      primary: "not-a-hex",
      primaryHover: "#000000",
      primarySoft: "#000000",
      primaryInk: "#000000",
      primaryRing: "rgba(0,0,0,1)",
    };
    expect(() => brandSchema.parse(raw)).toThrow();
  });

  it("loads brand from raw JSON object", () => {
    const brand = loadBrandFromJson({
      id: "default",
      name: "Credit Assistant",
      tagline: "Accountant Mode",
      logoMark: "CA",
      primary: "#1E55C9",
      primaryHover: "#1947AA",
      primarySoft: "#EAF0FB",
      primaryInk: "#1947AA",
      primaryRing: "rgba(30,85,201,0.22)",
    });
    expect(brand.id).toBe("default");
    expect(brand.cssVars["--brand-primary"]).toBe("#1E55C9");
    // CA-DS6/7: optional support/businessHours → null когда нет.
    expect(brand.support).toBeNull();
    expect(brand.businessHours).toBeNull();
  });

  it("loads brand with support + businessHours sections (CA-DS6/7/8)", () => {
    const brand = loadBrandFromJson({
      id: "default",
      name: "Credit Assistant",
      tagline: "Accountant Mode",
      logoMark: "CA",
      primary: "#1E55C9",
      primaryHover: "#1947AA",
      primarySoft: "#EAF0FB",
      primaryInk: "#1947AA",
      primaryRing: "rgba(30,85,201,0.22)",
      support: {
        phone: "+998 71 200-00-00",
        phoneTel: "tel:+998712000000",
        email: "support@example.uz",
        slack: { channel: "#help", workspace: "example" },
        docs: { url: "https://docs.example.uz", label: "docs.example.uz" },
        compliancePhone: "+998 71 200-00-77",
      },
      businessHours: {
        timezone: "Asia/Tashkent",
        weekdays: { start: "09:00", end: "18:00" },
      },
    });
    expect(brand.support?.email).toBe("support@example.uz");
    expect(brand.support?.compliancePhone).toBe("+998 71 200-00-77");
    expect(brand.businessHours?.timezone).toBe("Asia/Tashkent");
    expect(brand.businessHours?.weekdays.end).toBe("18:00");
  });

  it("rejects support.phoneTel without tel: prefix", () => {
    expect(() =>
      brandSchema.parse({
        id: "x",
        name: "x",
        tagline: "x",
        logoMark: "X",
        primary: "#000000",
        primaryHover: "#000000",
        primarySoft: "#000000",
        primaryInk: "#000000",
        primaryRing: "rgba(0,0,0,1)",
        support: {
          phone: "+998 71",
          phoneTel: "+998712000000",
          email: "a@b.uz",
          slack: { channel: "#h", workspace: "w" },
          docs: { url: "https://x.uz", label: "x" },
          compliancePhone: "+998 71",
        },
      }),
    ).toThrow();
  });
});
