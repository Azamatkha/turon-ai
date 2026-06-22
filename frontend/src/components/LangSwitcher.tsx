import { useState, useRef, useEffect, CSSProperties } from "react";

export type Lang = "uz" | "ru";

// Til ro'yxati: kod, to'liq nom, qisqa belgi
const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: "uz", label: "O‘zbekcha", short: "UZB" },
  { code: "ru", label: "Русский", short: "RUS" },
];

// Dumaloq (rounded) bayroq ikonkasi — flag-icons paketidan, doira shaklida kesilgan
function Flag({ code, size = 22 }: { code: Lang; size?: number }) {
  return (
    <span
      className={`fi fi-${code} fis`}
      style={{
        width: size,
        height: size,
        flex: "0 0 auto",
        display: "block",
        borderRadius: "50%",
        backgroundSize: "cover",
        backgroundPosition: "center",
        boxShadow: "0 0 0 1px rgba(22,66,91,.14), 0 1px 2px rgba(22,66,91,.18)",
      }}
    />
  );
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
    btnText: "#16425b",
    chevron: "#7d909a",
    btnShadow: "0 1px 3px rgba(22,66,91,.06)",
    menuBg: "#fff",
    menuBorder: "#e6eae3",
    menuShadow: "0 16px 40px rgba(13,33,45,.18)",
    itemText: "#16425b",
    itemActiveBg: "#eef3f6",
    itemHoverBg: "#f1f4ef",
    check: "#2f6690",
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
    <div ref={rootRef} style={{ position: "relative", ...style }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Tilni tanlash"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "7px 11px",
          background: t.btnBg,
          border: "1px solid " + t.btnBorder,
          borderRadius: "11px",
          cursor: "pointer",
          boxShadow: t.btnShadow,
          transition: "all .16s ease",
        }}
      >
        <Flag code={lang} size={20} />
        <span style={{ fontSize: "13px", fontWeight: 600, color: t.btnText }}>{current.short}</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke={t.chevron}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ transition: "transform .22s ease", transform: open ? "rotate(180deg)" : "none" }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            [align]: 0,
            width: "188px",
            zIndex: 50,
            background: t.menuBg,
            border: "1px solid " + t.menuBorder,
            borderRadius: "13px",
            padding: "5px",
            boxShadow: t.menuShadow,
            animation: "popIn .2s cubic-bezier(.2,.8,.3,1) both",
          }}
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
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "11px",
                  width: "100%",
                  padding: "9px 11px",
                  border: "none",
                  borderRadius: "9px",
                  background: active ? t.itemActiveBg : hovered ? t.itemHoverBg : "transparent",
                  cursor: "pointer",
                  transition: "background .14s ease",
                }}
              >
                <Flag code={o.code} size={24} />
                <span style={{ flex: 1, textAlign: "left", fontSize: "14px", fontWeight: 500, color: t.itemText }}>{o.label}</span>
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
