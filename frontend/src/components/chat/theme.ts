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
        cardBorder: "rgba(255,255,255,.12)",
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
        // Shisha (glassmorphism) — izoh yuqorida
        card: "rgba(255,255,255,.62)",
        cardBorder: "rgba(255,255,255,.70)",
        input: NAVY,
        disc: "#94A3B8",
        chipShadow: "0 1px 2px rgba(4, 33, 60, .06)",
      };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i)
export function getSideTokens(isDark: boolean): SideTokens {
  return {
    bg: isDark ? "#04162C" : NAVY,
    fg: "#F1F5F9",
    // Ilgari .55 edi — to'q ko'k fonda kontrast 3:1 dan past, ya'ni WCAG AA ni
    // o'tmasdi. .72 da matn o'qiladi, lekin baribir "ikkilamchi" ko'rinadi.
    sub: "rgba(203,213,225,.72)",
    active: "rgba(255,255,255,.15)",
    border: "rgba(255,255,255,.11)",
    logo: ACCENT_ON_DARK,
    btn: "rgba(255,255,255,.08)",
  };
}
