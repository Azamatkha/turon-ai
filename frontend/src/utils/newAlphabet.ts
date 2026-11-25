// O'zbek YANGI lotin alifbosi: amaldagi lotindan faqat 4 harf farq qiladi —
// o‘ -> ö, g‘ -> ğ, sh -> ş, ch -> ç. Shuning uchun "uz_new" tarjimalari alohida
// yozilmaydi: "uz" lug'atidan avtomatik hosil qilinadi (uz ga qo'shilgan har
// yangi matn yangi alifboda ham o'zi chiqadi).

import type { Lang } from "../types/lang";

// Tutuq belgisining barcha ko'rinishlari: ‘ ' ʻ ’ `
const OG_RE = /([oOgG])[‘'ʻ’`]/g;
const SH_CH_RE = /([sScC])([hH])/g;
// O'girilmaydigan bo'laklar: ```kod bloki```, `kod`, havola (https://...)
const SKIP_RE = /(```[\s\S]*?(?:```|$)|`[^`\n]*`|https?:\/\/[^\s"'<>)\]]+)/;
// So'z (ichida tutuq belgisi bo'lishi mumkin: "bo‘lim", "o'qing")
const WORD_RE = /[A-Za-z]+(?:[‘'ʻ’`][A-Za-z]*)*/g;

const OG: Record<string, string> = { o: "ö", O: "Ö", g: "ğ", G: "Ğ" };
const SH_CH: Record<string, string> = { s: "ş", S: "Ş", c: "ç", C: "Ç" };

// Chet so'z (Cashback, Mastercard, Windows): o'zbek lotinida "w" yo'q, "c" esa
// faqat "ch" tarkibida keladi — bunday so'z (brend, nom) o'zgartirilmaydi
function isForeign(word: string): boolean {
  return /[wW]/.test(word) || /[cC](?![hH])/.test(word);
}

function convertWord(word: string): string {
  if (isForeign(word)) return word;
  return word.replace(OG_RE, (_, ch: string) => OG[ch]).replace(SH_CH_RE, (_, ch: string) => SH_CH[ch]);
}

/** Amaldagi lotin matnni yangi alifboga o'giradi. Havola, kod va chet
 *  so'zlarga tegilmaydi; kirill/rus matn o'zgarmaydi. */
export function toNewAlphabet(text: string): string {
  return text
    .split(SKIP_RE)
    .map((part, i) => (i % 2 === 1 ? part : part.replace(WORD_RE, convertWord)))
    .join("");
}

/** Lug'atni (ichki obyekt, massiv, matn qaytaruvchi funksiyalar bilan) to'liq o'giradi. */
export function toNewAlphabetDeep<T>(value: T): T {
  if (typeof value === "string") return toNewAlphabet(value) as T;
  if (typeof value === "function") {
    const fn = value as unknown as (...args: unknown[]) => unknown;
    return ((...args: unknown[]) => toNewAlphabetDeep(fn(...args))) as T;
  }
  if (Array.isArray(value)) return value.map((v) => toNewAlphabetDeep(v)) as T;
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) out[k] = toNewAlphabetDeep(v);
    return out as T;
  }
  return value;
}

/** 3 tilli lug'atga "uz_new" ni qo'shadi — "uz" dan avtomatik o'girib. */
export function withNewAlphabet<T>(dict: Omit<Record<Lang, T>, "uz_new">): Record<Lang, T> {
  return { ...dict, uz_new: toNewAlphabetDeep(dict.uz) };
}
