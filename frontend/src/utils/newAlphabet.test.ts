import { describe, expect, it } from "vitest";
import { toNewAlphabet, toNewAlphabetDeep } from "./newAlphabet";

describe("toNewAlphabet", () => {
  it("faqat 4 harf: o‘ g‘ sh ch", () => {
    expect(toNewAlphabet("O‘zbekiston bo'yicha ishonch g‘alaba")).toBe("Özbekiston böyiça işonç ğalaba");
    expect(toNewAlphabet("SHARTNOMA Choy G‘ishtli")).toBe("ŞARTNOMA Çoy Ğiştli");
  });
  it("havolaga tegmaydi", () => {
    expect(toNewAlphabet("Manba: https://turonbank.uz/ch/sh — o‘qing")).toBe(
      "Manba: https://turonbank.uz/ch/sh — öqing"
    );
  });
  it("lug'at ichidagi funksiyalarni ham o'giradi", () => {
    const d = toNewAlphabetDeep({ a: "Chiqish", f: (n: number) => `${n} ta xabar o‘qildi`, l: ["sh"] });
    expect(d.a).toBe("Çiqiş");
    expect(d.f(3)).toBe("3 ta xabar öqildi");
    expect(d.l).toEqual(["ş"]);
  });
});

describe("toNewAlphabet — bot javobi", () => {
  it("chet so'z, kod va havolaga tegmaydi", () => {
    expect(toNewAlphabet("Cashback va Mastercard kartasi bo‘yicha shartlar")).toBe(
      "Cashback va Mastercard kartasi böyiça şartlar"
    );
    expect(toNewAlphabet("Buyruq: `ssh check` va\n```\nshow chart\n```\nchiqdi")).toBe(
      "Buyruq: `ssh check` va\n```\nshow chart\n```\nçiqdi"
    );
    expect(toNewAlphabet("[Shartlar](https://turonbank.uz/ch?sh=1)")).toBe("[Şartlar](https://turonbank.uz/ch?sh=1)");
  });
  it("kirill va rus matnga tegmaydi", () => {
    expect(toNewAlphabet("Шартлар — условия")).toBe("Шартлар — условия");
  });
});
