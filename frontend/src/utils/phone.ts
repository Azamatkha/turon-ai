// O'zbekiston telefon raqami bilan ishlash. Bazada raqam bo'shliqsiz turadi
// ("+998991234567"), foydalanuvchiga esa o'qiladigan ko'rinishda
// ko'rsatiladi ("+998 99 123 45 67"). Kiritishda +998 prefiksi qotirilgan —
// foydalanuvchi faqat qolgan 9 ta raqamni yozadi.

export const UZ_PHONE_PREFIX = "+998";
export const UZ_PHONE_DIGITS = 9;
export const IP_NUMBER_MAX_DIGITS = 4;

// "99 123 45 67" ko'rinishida guruhlaydi (to'liq bo'lmasa ham — yozish paytida)
export function groupLocalDigits(digits: string): string {
  const d = digits.replace(/\D/g, "").slice(0, UZ_PHONE_DIGITS);
  return [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)]
    .filter(Boolean)
    .join(" ");
}

// "+998991234567" -> "991234567" (tahrirlash maydoni uchun)
export function phoneLocalDigits(phone: string | null | undefined): string {
  if (!phone) return "";
  const d = phone.replace(/\D/g, "");
  return d.startsWith("998") ? d.slice(3) : d;
}

// "+998991234567" -> "+998 99 123 45 67"; bo'sh bo'lsa — ""
export function formatPhone(phone: string | null | undefined): string {
  const local = phoneLocalDigits(phone);
  return local ? `${UZ_PHONE_PREFIX} ${groupLocalDigits(local)}` : "";
}

// Maydondagi 9 ta raqamdan backendga yuboriladigan qiymat: "+998..." yoki ""
export function toApiPhone(localDigits: string): string {
  const d = localDigits.replace(/\D/g, "");
  return d ? `${UZ_PHONE_PREFIX}${d}` : "";
}

// Bo'sh (o'chirish) yoki aniq 9 ta raqam — ikkalasi ham to'g'ri
export function isValidLocalPhone(localDigits: string): boolean {
  const d = localDigits.replace(/\D/g, "");
  return d.length === 0 || d.length === UZ_PHONE_DIGITS;
}

// Bo'sh yoki 1-4 xonali son
export function isValidIpNumber(ip: string): boolean {
  return /^\d{0,4}$/.test(ip.trim());
}
