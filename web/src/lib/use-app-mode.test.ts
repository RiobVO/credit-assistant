import { describe, it, expect, vi } from "vitest";

vi.mock("./config", () => ({ APP_MODE: "bank" }));

import { useAppMode } from "./use-app-mode";

describe("useAppMode", () => {
  it("returns APP_MODE from config", () => {
    expect(useAppMode()).toBe("bank");
  });
});
