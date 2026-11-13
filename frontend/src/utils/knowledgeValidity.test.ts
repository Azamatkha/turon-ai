import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fmtIsoDate, validityState } from "./knowledgeValidity";

describe("knowledgeValidity", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 13, 12, 0, 0)); // 13.11.2026
  });
  afterEach(() => vi.useRealTimers());

  it("muddat holatini aniqlaydi", () => {
    expect(validityState(null)).toBeNull();
    expect(validityState("2026-11-12")).toBe("expired");
    expect(validityState("2026-11-13")).toBe("soon");
    expect(validityState("2026-11-20")).toBe("soon");
    expect(validityState("2026-11-21")).toBe("ok");
  });

  it("ISO sanani dd.mm.yyyy ga o'giradi", () => {
    expect(fmtIsoDate("2026-11-16")).toBe("16.11.2026");
    expect(fmtIsoDate("noto'g'ri")).toBe("noto'g'ri");
  });
});
