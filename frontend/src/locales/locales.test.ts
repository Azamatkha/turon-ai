import { describe, expect, it } from "vitest";
import { adminDict, chatDict, chatStaticDict, loginDict } from "./index";

// Kalitlar to'liqligini TypeScript tiplari ta'minlaydi; bu test esa tuzilma
// (ichki obyekt/massivlar) uchala tilda bir xilligini va bo'sh qolib ketgan
// tarjima yo'qligini tekshiradi.
function shape(value: unknown, path: string, out: Map<string, string>): void {
  if (Array.isArray(value)) {
    out.set(path, `array:${value.length}`);
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) shape(v, `${path}.${k}`, out);
  } else {
    out.set(path, typeof value);
  }
}

const dicts = { login: loginDict, chat: chatDict, chatStatic: chatStaticDict, admin: adminDict };

describe("locales", () => {
  for (const [name, dict] of Object.entries(dicts)) {
    it(`${name}: uz / uz_cyrl / ru tuzilmasi bir xil`, () => {
      const base = new Map<string, string>();
      shape(dict.uz, name, base);
      for (const lang of ["uz_cyrl", "ru"] as const) {
        const other = new Map<string, string>();
        shape(dict[lang], name, other);
        expect([...other.keys()].sort(), lang).toEqual([...base.keys()].sort());
      }
    });
  }
});
