import { useEffect, useRef, useState } from "react";

interface Option {
  value: string;
  label: string;
}

interface FilterSelectProps {
  value: string;
  options: Option[];
  onChange: (v: string) => void;
  fullWidth?: boolean;   // modal ichidagi maydon uchun — to'liq kenglik
  // Berilsa: hech narsa tanlanmaganda tugmada kulrang matn ko'rinadi va u
  // ro'yxatda option sifatida CHIQMAYDI (ya'ni uni tanlab bo'lmaydi).
  placeholder?: string;
}

// Maxsus dropdown (native <select> emas) — ichidagi optionlar ham styling qilinadi.
export default function FilterSelect({ value, options, onChange, fullWidth, placeholder }: FilterSelectProps) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);
  const showPlaceholder = !selected && !!placeholder;
  const current = selected ?? (placeholder ? undefined : options[0]);

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
    <div
      ref={rootRef}
      style={{
        position: "relative",
        display: fullWidth ? "block" : "inline-block",
        width: fullWidth ? "100%" : undefined,
        minWidth: fullWidth ? 0 : undefined,
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "9px 12px 9px 14px",
          minWidth: fullWidth ? 0 : 180,
          maxWidth: fullWidth ? "100%" : 320,
          width: fullWidth ? "100%" : undefined,
          boxSizing: "border-box",
          whiteSpace: "nowrap",
          borderRadius: 10,
          border: "1px solid var(--adm-border-input)",
          background: "var(--adm-card)",
          color: "var(--adm-text-strong)",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          boxShadow: "0 1px 2px rgba(0,57,120,.05)",
        }}
      >
        <span
          style={{
            flex: 1,
            minWidth: 0,
            textAlign: "left",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            color: showPlaceholder ? "var(--adm-text-muted-2)" : undefined,
            fontWeight: showPlaceholder ? 500 : undefined,
          }}
        >
          {showPlaceholder ? placeholder : current?.label}
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--adm-text-muted)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .18s ease" }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          style={{
            position: "absolute",
            left: 0,
            top: "calc(100% + 6px)",
            zIndex: 30,
            minWidth: "100%",
            maxWidth: fullWidth ? "100%" : undefined,
            boxSizing: "border-box",
            background: "var(--adm-card)",
            border: "1px solid var(--adm-border)",
            borderRadius: 12,
            boxShadow: "0 16px 40px rgba(15,23,42,.18)",
            padding: 6,
            maxHeight: 280,
            overflowY: "auto",
          }}
        >
          {options.map((o) => {
            const active = o.value === value;
            const hovered = hover === o.value;
            return (
              <button
                key={o.value}
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                onMouseEnter={() => setHover(o.value)}
                onMouseLeave={() => setHover(null)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  width: "100%",
                  padding: "9px 11px",
                  border: "none",
                  borderRadius: 8,
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  textAlign: "left",
                  color: "var(--adm-text-strong)",
                  background: active ? "rgba(11,95,165,.12)" : hovered ? "var(--adm-hover-2)" : "transparent",
                }}
              >
                {/* modalda (fullWidth) uzun nomlar o'ralsin — quti tashqarisiga
                    chiqmasin; filtr rejimida bir qatorda qolsin */}
                <span style={{ whiteSpace: fullWidth ? "normal" : "nowrap" }}>{o.label}</span>
                {active && (
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "var(--adm-accent)",
                      flex: "0 0 auto",
                    }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
