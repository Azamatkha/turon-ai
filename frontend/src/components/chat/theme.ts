import type { ThemeTokens, SideTokens } from "../../types/chat";

// Chat sahifasidagi xabar-bulutchalari va tugmalarning umumiy aksent rangi
export const ACCENT = "#3a7ca5";

// Asosiy mavzu (light/dark) rang to'plami — ChatHeader, MessageArea, Composer
// shu funksiyadan qaytgan obyektni o'qib, fonni/matn rangini moslashtiradi.
// Bitta joyda turgani uchun light/dark farqi faqat shu yerda boshqariladi.
export function getThemeTokens(isDark: boolean): ThemeTokens {
  return isDark
    ? { bg: "#0e2735", headBg: "rgba(14,39,53,.82)", headBorder: "rgba(255,255,255,.08)", strong: "#e8eef2", muted: "#8aa1ae", card: "#16384a", cardBorder: "rgba(255,255,255,.08)", input: "#e8eef2", disc: "#6b8290", chipShadow: "none" }
    : { bg: "#f3f5f8", headBg: "rgba(243,245,248,.82)", headBorder: "#e6e9ee", strong: "#173f73", muted: "#6b7d86", card: "#ffffff", cardBorder: "#e7eaef", input: "#173f73", disc: "#9aa3ad", chipShadow: "0 1px 2px rgba(23, 63, 115,.04)" };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i)
export function getSideTokens(isDark: boolean): SideTokens {
  return { bg: isDark ? "#102f41" : "#173f73", fg: "#eef2ef", sub: "rgba(217,220,214,.55)", active: "rgba(255,255,255,.13)", border: "rgba(255,255,255,.09)", logo: "#7fb3d2", btn: "rgba(255,255,255,.07)" };
}
