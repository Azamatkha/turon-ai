import { useEffect, useRef, useState } from "react";
import { DEPARTMENTS, deptLabel } from "../../services/departments";
import type { Lang } from "../../types/lang";
import styles from "./DepartmentSelect.module.css";

interface DepartmentSelectProps {
  value: string;                 // tanlangan departament (backendga ketadigan uz nomi)
  onChange: (v: string) => void;
  lang: Lang;
  placeholder: string;
}

// Departament tanlash — native <select> o'rniga custom dropdown (native selectning
// ochilgan ro'yxatini brauzer chizadi, uni bezab bo'lmaydi). Ko'rinishi register
// formasidagi boshqa maydonlar bilan bir xil.
export default function DepartmentSelect({ value, onChange, lang, placeholder }: DepartmentSelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Tashqariga bosilganda yoki Esc bosilganda yopamiz
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

  const selected = DEPARTMENTS.find((d) => d.uz === value);

  return (
    <div ref={rootRef} className={styles.root}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`${styles.trigger} ${open ? styles.triggerOpen : ""}`}
      >
        <span className={`${styles.value} ${selected ? "" : styles.placeholder}`}>
          {selected ? deptLabel(selected, lang) : placeholder}
        </span>
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div role="listbox" className={styles.menu}>
          {DEPARTMENTS.map((d) => {
            const active = d.uz === value;
            return (
              <button
                key={d.uz}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(d.uz);
                  setOpen(false);
                }}
                className={`${styles.menuItem} ${active ? styles.menuItemActive : ""}`}
              >
                <span className={styles.itemLabel}>{deptLabel(d, lang)}</span>
                {active && <span className={styles.dot} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
