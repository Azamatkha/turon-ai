import { describe, expect, it } from "vitest";
import {
  formatPhone,
  groupLocalDigits,
  isValidIpNumber,
  isValidLocalPhone,
  phoneLocalDigits,
  toApiPhone,
} from "./phone";

describe("phone", () => {
  it("raqamlarni 2-3-2-2 qilib guruhlaydi (to'liq bo'lmasa ham)", () => {
    expect(groupLocalDigits("991234567")).toBe("99 123 45 67");
    expect(groupLocalDigits("9912")).toBe("99 12");
    expect(groupLocalDigits("99-123-45-67-89")).toBe("99 123 45 67");
  });

  it("bazadagi raqamdan mahalliy qismni ajratadi", () => {
    expect(phoneLocalDigits("+998991234567")).toBe("991234567");
    expect(phoneLocalDigits(null)).toBe("");
  });

  it("ko'rsatish va API formatlari", () => {
    expect(formatPhone("+998991234567")).toBe("+998 99 123 45 67");
    expect(formatPhone("")).toBe("");
    expect(toApiPhone("99 123 45 67")).toBe("+998991234567");
    expect(toApiPhone("")).toBe("");
  });

  it("validatsiya: bo'sh yoki aniq 9 raqam; IP — 0-4 xonali", () => {
    expect(isValidLocalPhone("")).toBe(true);
    expect(isValidLocalPhone("991234567")).toBe(true);
    expect(isValidLocalPhone("99123")).toBe(false);
    expect(isValidIpNumber("1234")).toBe(true);
    expect(isValidIpNumber("12345")).toBe(false);
    expect(isValidIpNumber("12a")).toBe(false);
  });
});
