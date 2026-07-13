import type { ThemeTokens, SideTokens } from "../../types/chat";

// Chat sahifasidagi xabar-bulutchalari va tugmalarning umumiy aksent rangi
export const ACCENT = "#3a7ca5";

// Turon Bank brend (primary) rangi — logo, mavzu almashtirgich va boshqa
// brend elementlari shu navydan kelib chiqadi. Dark fonda ko'rinishi uchun
// PRIMARY_ON_DARK ishlatiladi.
export const PRIMARY = "#1B4B7A";
export const PRIMARY_ON_DARK = "#7fb3d2";

// Asosiy mavzu (light/dark) rang to'plami — ChatHeader, MessageArea, Composer
// shu funksiyadan qaytgan obyektni o'qib, fonni/matn rangini moslashtiradi.
// Bitta joyda turgani uchun light/dark farqi faqat shu yerda boshqariladi.
export function getThemeTokens(isDark: boolean): ThemeTokens {
  return isDark
    ? { bg: "#0d1e33", headBg: "rgba(13,30,51,.82)", headBorder: "rgba(255,255,255,.08)", strong: "#e8eef2", muted: "#94a5bc", card: "#16283f", cardBorder: "rgba(255,255,255,.08)", input: "#e8eef2", disc: "#7e8fa6", chipShadow: "none" }
    : { bg: "#f3f5f8", headBg: "rgba(243,245,248,.82)", headBorder: "#e6e9ee", strong: "#173f73", muted: "#5b6d78", card: "#ffffff", cardBorder: "#e7eaef", input: "#173f73", disc: "#7c8590", chipShadow: "0 1px 2px rgba(23, 63, 115,.04)" };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i)
export function getSideTokens(isDark: boolean): SideTokens {
  return { bg: isDark ? "#152a45" : "#173f73", fg: "#eef2ef", sub: "rgba(217,220,214,.55)", active: "rgba(255,255,255,.13)", border: "rgba(255,255,255,.09)", logo: "#7fb3d2", btn: "rgba(255,255,255,.07)" };
}
