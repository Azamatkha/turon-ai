import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { MdDialpad } from "react-icons/md";
import {
  fetchDirectoryDepartments,
  searchDirectory,
  type DirectoryEntry,
} from "../../services/directoryService";
import { ACCENT, PRIMARY_ON_DARK } from "./theme";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./DirectoryModal.module.css";

interface DirectoryModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

// Backend ham shu chegarani tekshiradi (usecases/directory.py -> MIN_SEARCH_LEN)
const MIN_SEARCH_LEN = 2;

/**
 * Ichki raqamlar ma'lumotnomasi: bo'lim tanlanadi -> xodimlar ro'yxati ->
 * xodim tanlanganda uning ismi, lavozimi, bo'limi va IP (ichki) raqami.
 * Telefon va boshqa shaxsiy ma'lumotlar ATAYLAB ko'rsatilmaydi (backend ham
 * qaytarmaydi).
 */
export default function DirectoryModal({ tk, isDark, s, onClose }: DirectoryModalProps) {
  const [departments, setDepartments] = useState<string[]>([]);
  const [department, setDepartment] = useState("");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<DirectoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<DirectoryEntry | null>(null);

  const accent = isDark ? PRIMARY_ON_DARK : ACCENT;
  const cardBg = "var(--tu-glass-bg-soft)";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Avval kartochkadan ro'yxatga qaytadi, keyin oyna yopiladi
      if (selected) setSelected(null);
      else onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, selected]);

  useEffect(() => {
    fetchDirectoryDepartments()
      .then(setDepartments)
      .catch(() => setFailed(true));
  }, []);

  const q = query.trim();
  const canSearch = Boolean(department) || q.length >= MIN_SEARCH_LEN;

  // Bo'lim yoki qidiruv o'zgarsa — ro'yxat qayta yuklanadi (yozish paytida
  // har harfda so'rov ketmasin — 300ms kutiladi)
  useEffect(() => {
    if (!canSearch) {
      setItems([]);
      return;
    }
    let alive = true;
    const id = setTimeout(() => {
      setLoading(true);
      searchDirectory({ department: department || undefined, q: q.length >= MIN_SEARCH_LEN ? q : undefined })
        .then((res) => {
          if (!alive) return;
          setItems(res);
          setFailed(false);
        })
        .catch(() => alive && setFailed(true))
        .finally(() => alive && setLoading(false));
    }, 300);
    return () => {
      alive = false;
      clearTimeout(id);
    };
  }, [department, q, canSearch]);

  const fieldStyle = { background: cardBg, color: tk.input, borderColor: tk.cardBorder };

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={s.dirTitle}
      >
        <div className={styles.head}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>
            <MdDialpad size={21} color={accent} />
            {s.dirTitle}
          </div>
          <button className={styles.closeBtn} style={{ color: tk.muted }} onClick={onClose} aria-label={s.close}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        {selected ? (
          <div className={styles.body}>
            <button type="button" className={styles.backBtn} style={{ color: accent }} onClick={() => setSelected(null)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              {s.dirBack}
            </button>
            <div className={styles.card} style={{ background: cardBg, borderColor: tk.cardBorder }}>
              <div className={styles.avatar}>{selected.full_name.charAt(0).toUpperCase()}</div>
              <div className={styles.cardName} style={{ color: tk.strong }}>{selected.full_name}</div>
              <dl className={styles.facts}>
                <div className={styles.fact}>
                  <dt style={{ color: tk.muted }}>{s.dirPosition}</dt>
                  <dd style={{ color: tk.strong }}>{selected.position || "—"}</dd>
                </div>
                <div className={styles.fact}>
                  <dt style={{ color: tk.muted }}>{s.dirDepartment}</dt>
                  <dd style={{ color: tk.strong }}>{selected.department || "—"}</dd>
                </div>
              </dl>
              <div className={styles.ipBox} style={{ borderColor: tk.cardBorder }}>
                <span className={styles.ipLabel} style={{ color: tk.muted }}>{s.dirIp}</span>
                {selected.ip_number ? (
                  <span className={styles.ipValue} style={{ color: accent }}>{selected.ip_number}</span>
                ) : (
                  <span className={styles.ipNone} style={{ color: tk.disc }}>{s.dirNoIp}</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.body}>
            <label className={styles.label} style={{ color: tk.muted }} htmlFor="dir-dept">{s.dirDepartment}</label>
            <select
              id="dir-dept"
              className={styles.input}
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              style={fieldStyle}
            >
              <option value="">{s.dirPickDepartment}</option>
              {departments.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>

            <input
              className={`${styles.input} ${styles.search}`}
              value={query}
              maxLength={60}
              placeholder={s.dirSearchPh}
              onChange={(e) => setQuery(e.target.value)}
              style={fieldStyle}
              aria-label={s.dirSearchPh}
            />

            <div className={styles.list} aria-busy={loading}>
              {failed ? (
                <div className={styles.state} style={{ color: "#DC2626" }}>{s.dirError}</div>
              ) : !canSearch ? (
                <div className={styles.state} style={{ color: tk.muted }}>{s.dirHint}</div>
              ) : loading && items.length === 0 ? (
                <div className={styles.state} style={{ color: tk.muted }}>{s.dirLoading}</div>
              ) : items.length === 0 ? (
                <div className={styles.state} style={{ color: tk.muted }}>{s.dirEmpty}</div>
              ) : (
                items.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className={styles.row}
                    style={{ borderColor: tk.cardBorder }}
                    onClick={() => setSelected(u)}
                  >
                    <span className={styles.rowAvatar}>{u.full_name.charAt(0).toUpperCase()}</span>
                    <span className={styles.rowBody}>
                      <span className={styles.rowName} style={{ color: tk.strong }}>{u.full_name}</span>
                      <span className={styles.rowSub} style={{ color: tk.muted }}>
                        {/* Bo'lim tanlanmagan (ism bo'yicha qidiruv) bo'lsa — bo'lim ham ko'rinsin */}
                        {[u.position, department ? null : u.department].filter(Boolean).join(" · ") || "—"}
                      </span>
                    </span>
                    {u.ip_number && (
                      <span className={styles.rowIp} style={{ color: accent }}>{u.ip_number}</span>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
