import { describe, expect, it } from "vitest";
import { pageList } from "./pageList";

describe("pageList", () => {
  it("kam sahifada hammasini ko'rsatadi", () => {
    expect(pageList(1, 5)).toEqual([1, 2, 3, 4, 5]);
  });

  it("o'rtada bo'lsa ikki tomonda … qo'yadi", () => {
    expect(pageList(6, 12)).toEqual([1, null, 5, 6, 7, null, 12]);
  });

  it("boshida bo'lsa faqat oxirida …", () => {
    expect(pageList(1, 12)).toEqual([1, 2, null, 12]);
  });
});
