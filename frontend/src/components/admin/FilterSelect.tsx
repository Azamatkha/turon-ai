import { useEffect, useRef, useState } from "react";

interface Option {
  value: string;
  label: string;
}

interface FilterSelectProps {
  value: string;
  options: Option[];
  onChange: (v: string) => void;
}

// Maxsus dropdown (native <select> emas) — ichidagi optionlar ham styling qilinadi.
export default function FilterSelect({ value, options, onChange }: FilterSelectProps) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const current = options.find((o) => o.value === value) ?? options[0];

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
    <div ref={rootRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "9px 12px 9px 14px",
          minWidth: 180,
          borderRadius: 10,
          border: "1px solid #dde2dc",
          background: "#fff",
          color: "#173f73",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          boxShadow: "0 1px 2px rgba(23,63,115,.05)",
        }}
      >
        <span style={{ flex: 1, textAlign: "left" }}>{current?.label}</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#7d909a"
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
            background: "#fff",
            border: "1px solid #e6eae3",
            borderRadius: 12,
            boxShadow: "0 16px 40px rgba(13,33,45,.18)",
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
                  color: "#173f73",
                  background: active ? "#eef3f6" : hovered ? "#f1f4ef" : "transparent",
                }}
              >
                <span>{o.label}</span>
                {active && (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2a6f97" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
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
