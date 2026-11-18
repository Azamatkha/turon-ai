import { describe, expect, it } from "vitest";
import { docKind, docMessageText, parseDocMessage, validateDoc, DOC_MAX_BYTES } from "./documentService";

describe("hujjatli xabar", () => {
  it("fayl nomi va savolni ajratadi", () => {
    const text = docMessageText("oktabr karta.xlsx", "manabu excelda nima bor");
    expect(parseDocMessage(text)).toEqual({ name: "oktabr karta.xlsx", question: "manabu excelda nima bor" });
  });

  it("savolsiz hujjat", () => {
    expect(parseDocMessage(docMessageText("buyruq.pdf", ""))).toEqual({ name: "buyruq.pdf", question: "" });
  });

  it("oddiy matn kartochka bo'lmaydi", () => {
    expect(parseDocMessage("Salom")).toBeNull();
    expect(parseDocMessage("📎 shunchaki belgi")).toBeNull();
  });

  it("tur yorlig'i", () => {
    expect(docKind("a.XLSX").label).toBe("XLSX");
    expect(docKind("a.pdf").label).toBe("PDF");
  });

  it("tekshiruv: tur va hajm", () => {
    expect(validateDoc(new File(["x"], "a.exe"))).toBe("unsupported");
    const big = { name: "a.pdf", size: DOC_MAX_BYTES + 1 } as File;
    expect(validateDoc(big)).toBe("tooLarge");
    expect(validateDoc(new File(["x"], "a.docx"))).toBeNull();
  });
});
