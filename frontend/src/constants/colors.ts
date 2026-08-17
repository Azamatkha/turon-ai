// Brend rang palitrasi — JS tomondan (inline style, canvas, SVG) kerak bo'ladigan ranglar.
//
// YAGONA MANBA: `src/index.css` dagi CSS o'zgaruvchilari (--tu-*).
// Bu yerdagi qiymatlar o'shalarning KO'CHIRMASI — canvas va inline style
// `var(--...)` ni tushunmagani uchun literal hex kerak bo'ladi.
//
// Rang o'zgartirmoqchi bo'lsangiz: AVVAL index.css dagi --tu-* ni o'zgartiring,
// so'ng shu fayldagi mos qiymatni yangilang. .module.css fayllari endi
// literal hex EMAS, to'g'ridan-to'g'ri var(--tu-*) ishlatishi kerak.

/* --- Brend ko'k shkalasi (index.css: --tu-blue-*) --- */
export const BLUE_50 = "#F0F3FD";
export const BLUE_100 = "#E3E9FC";
export const BLUE_200 = "#C6D0F6";
export const BLUE_300 = "#A3B3EE";
export const BLUE_400 = "#8195E6";
export const BLUE_500 = "#5A78E0";
export const BLUE_600 = "#4059BE";
export const BLUE_700 = "#30469C";
export const BLUE_800 = "#243A81";
export const BLUE_900 = "#193070";
export const BLUE_950 = "#0E1B42";

/* --- Semantik nomlar (eski kod shu nomlarni import qiladi) --- */
export const NAVY = BLUE_900; // logotip, sidebar — asosiy brend rangi
export const MID_BLUE = BLUE_800; // navy ning ochroq pog'onasi (hover/gradient)
export const ACCENT = BLUE_600; // interaktiv ko'k — havola, faol holat, CTA
export const ACCENT_VIVID = BLUE_500; // diqqat tortadigan yorqin ko'k
export const LIGHT_BLUE = BLUE_300; // dark fonda accent
export const PALE_BLUE = BLUE_100; // juda ochiq ko'k fon/chegara

/* Dark rejimdagi aksent — qora-ko'k fonda 7:1 kontrast (WCAG AAA) */
export const ACCENT_ON_DARK = "#A6B6F2";

/* --- Brend uchligi (index.css: --tu-primary / --tu-secondary / --tu-violet) --- */
export const PRIMARY_COLOR = "#193070";
export const SECONDARY_COLOR = "#5A78E0";

/* --- Sidebar gradienti uchun binafsha-indigo juftlik ---
   Faqat DEKORATIV: sidebar foni, hover/faol holat tovlanishi. Matn yoki
   ikonka rangi sifatida ishlatilmaydi (oq fonda kontrasti yetarli emas). */
export const VIOLET = "#7B4DFF";
export const INDIGO = "#5A78E0";

/* --- Neytral --- */
export const TEXT_STRONG = "#334155";
export const TEXT_MUTED = "#64748B";
export const TEXT_FAINT = "#94A3B8";
export const TEXT_PLACEHOLDER = "#94A3B8";

export const BORDER = "#CBD5E1";
export const BORDER_SOFT = "#E2E8F0";

export const SURFACE = "#F8FAFC";

/* --- Holat ranglari (kuchaytirilgan) --- */
export const SUCCESS = "#047857";
export const ERROR = "#DC2626";
export const WARNING = "#B45309";
