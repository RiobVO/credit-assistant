// CA-DS29: locale cookie parsing — fallback chain depends on this.

import { describe, expect, it } from "vitest";

import { LOCALE_COOKIE, LOCALE_VALUES, readLocaleCookie } from "./locale-cookie";

describe("locale-cookie", () => {
  it("LOCALE_COOKIE is 'ca_locale' (consistent с ca_access/ca_refresh)", () => {
    expect(LOCALE_COOKIE).toBe("ca_locale");
  });

  it("LOCALE_VALUES охватывает только ru + uz", () => {
    expect(LOCALE_VALUES).toEqual(["ru", "uz"]);
  });

  it("readLocaleCookie('ru') → 'ru'", () => {
    expect(readLocaleCookie("ru")).toBe("ru");
  });

  it("readLocaleCookie('uz') → 'uz'", () => {
    expect(readLocaleCookie("uz")).toBe("uz");
  });

  it("readLocaleCookie(undefined) → null (cookie not set)", () => {
    expect(readLocaleCookie(undefined)).toBeNull();
  });

  it("readLocaleCookie('fr') → null (unsupported locale)", () => {
    expect(readLocaleCookie("fr")).toBeNull();
  });

  it("readLocaleCookie('garbage') → null (invalid value)", () => {
    expect(readLocaleCookie("garbage")).toBeNull();
  });

  it("readLocaleCookie('') → null (empty cookie value)", () => {
    expect(readLocaleCookie("")).toBeNull();
  });
});
