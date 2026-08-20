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
        bg: "#0A1029",
        headBg: "rgba(10,16,41,.86)",
        headBorder: "rgba(154,172,236,.16)",
        strong: "#DFE4F5",
        muted: "#98A2CC",
        // Shisha (glassmorphism): fon to'liq shaffofmas emas. Blur esa
        // CSS modullardagi `backdrop-filter: var(--tu-glass-blur)` orqali.
        card: "rgba(21,29,63,.58)",
        bubble: "rgba(21,29,63,.40)",
        // Foydalanuvchi xabari — YORUG'ROQ ko'k gradient. Sahifa foni
        // (#0A1029) dan yuqorida turadi, ya'ni bulutcha fonga "botib"
        // ketmaydi va undan qora bo'lib ham ajralmaydi.
        bubbleUser: "linear-gradient(176deg, rgb(0 53 117) 0%, rgb(29 58 97) 60%, rgb(54 73 121) 100%)",
        cardBorder: "rgba(154,172,236,.18)",
        input: "#DFE4F5",
        disc: "#6E79A6",
        chipShadow: "none",
      }
    : {
        bg: "#F6F7FC",
        headBg: "rgba(246,247,252,.86)",
        headBorder: "#DCE1EF",
        strong: NAVY,
        muted: "#626D93",
        // Shisha (glassmorphism) — izoh yuqorida.
        // Chegara OQ emas, ko'kish: oq chiziq oq fonda ko'rinmasdi va
        // tugmalar "ramkasiz" bo'lib qolgandi.
        card: "rgba(255,255,255,.62)",
        bubble: "rgba(255,255,255,.42)",
        bubbleUser: "linear-gradient(176deg, #193070 0%, #24397F 60%, #33459B 100%)",
        cardBorder: "rgba(25,48,112,.16)",
        input: NAVY,
        disc: "#8F99BB",
        chipShadow: "0 1px 2px rgba(14, 27, 66, .06)",
      };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i).
//
// Fon TEKIS rang emas, diagonal gradient — lekin ATAYLAB jim: asosini brend
// primary (#193070) tutadi, secondary (#5A78E0) va binafsha (#7B4DFF) faqat
// pastki qismida sezilar-sezilmas tovlanadi. (Ilgari to'liq #5A78E0 → #7B4DFF
// ga chiqardi — sidebar juda yorqin/rang-barang bo'lib, sahifaning tinch
// foniga mos tushmadi.)
//
// GRADIENT UCH EMAS, BESH NUQTALI. Ilgari uchta to'xtash nuqtasi bor edi
// (#193070 → #223780 → #2C2C6E) va oxirgi rang loyqa binafsha-kulrang edi:
// ko'kdan unga o'tish keskin sezilib, panel pastki uchdan birida "kirlanib"
// ko'rinardi, umumiy ko'rinishi esa tekis rangdan farq qilmasdi.
//
// Endi yo'l aniq: to'q navy -> brend navy -> indigo -> binafsha-indigo ->
// binafsha. Pog'onalar ko'p bo'lgani uchun hech qayerda chegara ko'rinmaydi,
// lekin yuqori va quyi uchning rangi sezilarli farq qiladi — gradient
// "bor"ligi bilinadi. Burchak 176° dan 162° ga o'zgardi: deyarli tik gradient
// tekis rangdek o'qilardi.
//
// CHEGARA: pastki uch baribir brend doirasida qoladi (#4A34A0 — binafsha
// #7B4DFF ning to'qroq varianti). To'liq #7B4DFF gacha chiqarish sinab
// ko'rilgan va rad etilgan: sidebar neonday yorqin bo'lib, sahifaning tinch
// lavanda foniga mos tushmagan.
//
// MUHIM: bu funksiya CHAT va ADMIN sidebar'ining IKKALASIGA xizmat qiladi —
// ikki panel bir xil ko'rinishi kerak, farq faqat ichidagi funksiyalarda.
export function getSideTokens(isDark: boolean): SideTokens {
  return {
    bg: isDark
      ? `linear-gradient(162deg, #05081C 0%, #0C1338 30%, #141C55 58%, #1E1C6A 82%, #2A1E72 100%)`
      : `linear-gradient(162deg, #0D1A4A 0%, ${NAVY} 26%, #27378F 52%, #3A3599 78%, #4A34A0 100%)`,
    fg: "#F1F3FB",
    // Ilgari .55 edi — to'q ko'k fonda kontrast 3:1 dan past, ya'ni WCAG AA ni
    // o'tmasdi. .72 da matn o'qiladi, lekin baribir "ikkilamchi" ko'rinadi.
    sub: "rgba(223,228,245,.72)",
    active: "rgba(255,255,255,.14)",
    border: "rgba(255,255,255,.12)",
    logo: ACCENT_ON_DARK,
    // "Yangi suhbat" tugmasi — oq shisha, ustida juda yengil indigo tovlanish
    btn: "linear-gradient(135deg, rgba(255,255,255,.12) 0%, rgba(90,120,224,.18) 100%)",
  };
}
