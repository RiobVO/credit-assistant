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
  });
});
