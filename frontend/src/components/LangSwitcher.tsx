import { useState, useRef, useEffect, CSSProperties } from "react";
import type { Lang } from "../types/lang";
import styles from "./LangSwitcher.module.css";

export type { Lang };

// Til ro'yxati: kod, to'liq nom, qisqa belgi
// "uz" va "uz_cyrl" bir xil davlat bayrog'iga ega (O'zbekiston) — faqat yozuvi farq qiladi
const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: "uz", label: "O‘zbekcha (lotin)", short: "UZB" },
  { code: "uz_cyrl", label: "Ўзбекча (кирилл)", short: "УЗБ" },
  { code: "ru", label: "Русский", short: "RUS" },
];

// Bayroq ikonkasi davlat kodiga bog'lanadi, til kodiga emas (uz/uz_cyrl bittasini ulashadi)
const FLAG_COUNTRY: Record<Lang, string> = { uz: "uz", uz_cyrl: "uz", ru: "ru" };

// Dumaloq (rounded) bayroq ikonkasi — flag-icons paketidan, doira shaklida kesilgan
function Flag({ code, size = 22 }: { code: Lang; size?: number }) {
  return <span className={`fi fi-${FLAG_COUNTRY[code]} fis ${styles.flag}`} style={{ width: size, height: size }} />;
}

interface ThemeTokens {
  btnBg: string;
  btnBorder: string;
  btnText: string;
  chevron: string;
  btnShadow: string;
  menuBg: string;
  menuBorder: string;
  menuShadow: string;
  itemText: string;
  itemActiveBg: string;
  itemHoverBg: string;
  check: string;
}

const THEMES: Record<"light" | "dark", ThemeTokens> = {
  light: {
    btnBg: "#fff",
    btnBorder: "#dde2dc",
    btnText: "#173f73",
    chevron: "#7d909a",
    btnShadow: "0 1px 3px rgba(23, 63, 115,.06)",
    menuBg: "#fff",
    menuBorder: "#e6eae3",
    menuShadow: "0 16px 40px rgba(13,33,45,.18)",
    itemText: "#173f73",
    itemActiveBg: "#eef3f6",
    itemHoverBg: "#f1f4ef",
    check: "#2a6f97",
  },
  dark: {
    btnBg: "rgba(255,255,255,.08)",
    btnBorder: "rgba(255,255,255,.14)",
    btnText: "#e8eef2",
    chevron: "rgba(232,238,242,.6)",
    btnShadow: "none",
    menuBg: "#173a4d",
    menuBorder: "rgba(255,255,255,.1)",
    menuShadow: "0 16px 40px rgba(0,0,0,.4)",
    itemText: "#e8eef2",
    itemActiveBg: "rgba(255,255,255,.1)",
    itemHoverBg: "rgba(255,255,255,.06)",
    check: "#7fb3d2",
  },
};

interface LangSwitcherProps {
  lang: Lang;
  onChange: (l: Lang) => void;
  theme?: "light" | "dark";
  align?: "left" | "right";
  style?: CSSProperties;
}

export default function LangSwitcher({ lang, onChange, theme = "light", align = "right", style }: LangSwitcherProps) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState<Lang | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const t = THEMES[theme];
  const current = LANGS.find((l) => l.code === lang) ?? LANGS[0];

  // Tashqariga bosilganda yoki Esc bosilganda yopish
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div ref={rootRef} className={styles.root} style={style}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Tilni tanlash"
        className={styles.trigger}
        style={{ background: t.btnBg, border: "1px solid " + t.btnBorder, boxShadow: t.btnShadow }}
      >
        <Flag code={lang} size={20} />
        <span className={styles.shortLabel} style={{ color: t.btnText }}>{current.short}</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke={t.chevron}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className={styles.menu}
          style={{ [align]: 0, background: t.menuBg, border: "1px solid " + t.menuBorder, boxShadow: t.menuShadow }}
        >
          {LANGS.map((o) => {
            const active = o.code === lang;
            const hovered = hover === o.code;
            return (
              <button
                key={o.code}
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(o.code);
                  setOpen(false);
                }}
                onMouseEnter={() => setHover(o.code)}
                onMouseLeave={() => setHover(null)}
                className={styles.menuItem}
                style={{ background: active ? t.itemActiveBg : hovered ? t.itemHoverBg : "transparent" }}
              >
                <Flag code={o.code} size={24} />
                <span className={styles.itemLabel} style={{ color: t.itemText }}>{o.label}</span>
                {active && (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={t.check} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
