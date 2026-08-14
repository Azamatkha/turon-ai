import type { ThemeTokens, SideTokens } from "../../types/chat";
import { ACCENT as BRAND_ACCENT, ACCENT_ON_DARK, NAVY } from "../../constants/colors";

// Chat sahifasidagi xabar-bulutchalari va tugmalarning umumiy aksent rangi.
// Qiymat `constants/colors.ts` dan keladi — u esa index.css dagi --tu-* ning
// ko'chirmasi. Ya'ni rang bitta joydan boshqariladi.
export const ACCENT = BRAND_ACCENT;

// Turon Bank brend (primary) rangi — logo, mavzu almashtirgich va boshqa
// brend elementlari shu navydan kelib chiqadi. Dark fonda ko'rinishi uchun
// PRIMARY_ON_DARK ishlatiladi (qora-ko'k fonda 7:1 kontrast — WCAG AAA).
export const PRIMARY = NAVY;
export const PRIMARY_ON_DARK = ACCENT_ON_DARK;

// Asosiy mavzu (light/dark) rang to'plami — ChatHeader, MessageArea, Composer
// shu funksiyadan qaytgan obyektni o'qib, fonni/matn rangini moslashtiradi.
// Bitta joyda turgani uchun light/dark farqi faqat shu yerda boshqariladi.
export function getThemeTokens(isDark: boolean): ThemeTokens {
  return isDark
    ? {
        bg: "#061A31",
        headBg: "rgba(6,26,49,.86)",
        headBorder: "rgba(255,255,255,.10)",
        strong: "#E2E8F0",
        muted: "#94A3B8",
        // Shisha (glassmorphism): fon to'liq shaffofmas emas. Blur esa
        // CSS modullardagi `backdrop-filter: var(--tu-glass-blur)` orqali.
        card: "rgba(12,41,73,.58)",
        cardBorder: "rgba(255,255,255,.18)",
        input: "#E2E8F0",
        disc: "#64748B",
        chipShadow: "none",
      }
    : {
        bg: "#F8FAFC",
        headBg: "rgba(248,250,252,.86)",
        headBorder: "#E2E8F0",
        strong: NAVY,
        muted: "#64748B",
        // Shisha (glassmorphism) — izoh yuqorida.
        // Chegara OQ emas, ko'kish: oq chiziq oq fonda ko'rinmasdi va
        // tugmalar "ramkasiz" bo'lib qolgandi.
        card: "rgba(255,255,255,.62)",
        cardBorder: "rgba(0,57,120,.16)",
        input: NAVY,
        disc: "#94A3B8",
        chipShadow: "0 1px 2px rgba(4, 33, 60, .06)",
      };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i).
//
// Fon endi TEKIS rang emas, diagonal gradient: brend navy (#003978) dan indigo
// (#5A78E0) orqali binafsha (#7B4DFF) ga o'tadi. Rangi to'liq shaffofmas emas —
// Sidebar.module.css dagi `backdrop-filter` bilan birga "shisha" effektini beradi.
export function getSideTokens(isDark: boolean): SideTokens {
  return {
    bg: isDark
      ? `linear-gradient(168deg, rgba(4,22,44,.94) 0%, rgba(30,32,86,.94) 52%, rgba(62,42,124,.94) 100%)`
      : `linear-gradient(168deg, ${NAVY} 0%, rgba(90,120,224,.92) 58%, rgba(123,77,255,.90) 100%)`,
    fg: "#F1F5F9",
    // Ilgari .55 edi — to'q ko'k fonda kontrast 3:1 dan past, ya'ni WCAG AA ni
    // o'tmasdi. .72 da matn o'qiladi, lekin baribir "ikkilamchi" ko'rinadi.
    sub: "rgba(203,213,225,.72)",
    active: "rgba(255,255,255,.16)",
    border: "rgba(255,255,255,.14)",
    logo: ACCENT_ON_DARK,
    // "Yangi suhbat" tugmasi — binafsha→indigo shisha to'ldirmasi
    btn: "linear-gradient(135deg, rgba(123,77,255,.55) 0%, rgba(90,120,224,.42) 100%)",
  };
}
