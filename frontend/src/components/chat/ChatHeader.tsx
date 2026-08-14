import { useState } from "react";
import {
  MdCurrencyExchange,
  MdOutlineAdminPanelSettings,
  MdReportGmailerrorred,
} from "react-icons/md";
import { FaCalculator } from "react-icons/fa6";
import LangSwitcher from "../LangSwitcher";
import ThemeToggle from "./ThemeToggle";
import CalculatorModal from "./CalculatorModal";
import RatesModal from "./RatesModal";
import NotificationsBell from "./NotificationsBell";
import ReportModal from "./ReportModal";
import HButton from "../common/HButton";
import type { Lang } from "../../types/lang";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ChatHeader.module.css";

interface ChatHeaderProps {
  title: string;
  lang: Lang;
  setLang: (l: Lang) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  tk: ThemeTokens;
  isAdmin?: boolean;
  onAdmin?: () => void;
  editableTitle?: boolean;
  onRenameTitle?: (next: string) => void;
  s: ChatStaticStrings;
}

export default function ChatHeader({
  title, lang, setLang, isDark, onToggleTheme, tk, isAdmin, onAdmin, editableTitle, onRenameTitle, s,
}: ChatHeaderProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(title);
  const [calcOpen, setCalcOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [ratesOpen, setRatesOpen] = useState(false);

  const startEdit = () => {
    if (!editableTitle || !onRenameTitle) return;
    setValue(title);
    setEditing(true);
  };
  const commit = () => {
    const next = value.trim();
    if (next && next !== title) onRenameTitle?.(next);
    setEditing(false);
  };

  return (
    <header className={styles.header} style={{ borderBottom: "none", background: "transparent" }}>
      <div className={styles.left}>
        {editing ? (
          <input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") setEditing(false);
            }}
            className={styles.title}
            style={{
              color: tk.strong,
              background: "transparent",
              border: "1px solid " + tk.headBorder,
              borderRadius: 8,
              padding: "3px 9px",
              outline: "none",
              minWidth: 220,
            }}
          />
        ) : (
          <>
            <div
              className={styles.title}
              style={{ color: tk.strong, cursor: editableTitle ? "text" : "default" }}
              onDoubleClick={startEdit}
              data-tip={editableTitle ? "Nomini o‘zgartirish uchun ikki marta bosing" : undefined}
            >
              {title}
            </div>
            {editableTitle && (
              <button onClick={startEdit} data-tip="Suhbat nomini tahrirlash" aria-label="Suhbat nomini tahrirlash" className={styles.renameBtn} style={{ color: tk.muted }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" /></svg>
              </button>
            )}
          </>
        )}
      </div>

      <div className={styles.right}>
        {isAdmin && (
          <HButton
            onClick={() => onAdmin?.()}
            data-tip={s.adminPanel}
            aria-label={s.adminPanel}
            className={styles.adminBtn}
            baseStyle={{ border: "1px solid var(--tu-glass-border)", color: isDark ? "#E2E8F0" : "#003978", backdropFilter: "var(--tu-glass-blur)", WebkitBackdropFilter: "var(--tu-glass-blur)" }}
            /* Fon hover'i CSS'da (.adminBtn:hover) — bu yerda `background`
             berilsa, u qisqartma xossa bo'lgani uchun gradientni o'chirardi */
          hoverStyle={{ transform: "translateY(-1px)" }}
          >
            <MdOutlineAdminPanelSettings size={20} />
          </HButton>
        )}
        <HButton
          onClick={() => setRatesOpen(true)}
          data-tip={s.rates}
          aria-label={s.rates}
          className={styles.adminBtn}
          baseStyle={{ border: "1px solid var(--tu-glass-border)", color: isDark ? "#E2E8F0" : "#003978", backdropFilter: "var(--tu-glass-blur)", WebkitBackdropFilter: "var(--tu-glass-blur)" }}
          /* Fon hover'i CSS'da (.adminBtn:hover) — bu yerda `background`
             berilsa, u qisqartma xossa bo'lgani uchun gradientni o'chirardi */
          hoverStyle={{ transform: "translateY(-1px)" }}
        >
          <MdCurrencyExchange size={20} />
        </HButton>
        <HButton
          onClick={() => setCalcOpen(true)}
          data-tip={s.calculator}
          aria-label={s.calculator}
          className={styles.adminBtn}
          baseStyle={{ border: "1px solid var(--tu-glass-border)", color: isDark ? "#E2E8F0" : "#003978", backdropFilter: "var(--tu-glass-blur)", WebkitBackdropFilter: "var(--tu-glass-blur)" }}
          /* Fon hover'i CSS'da (.adminBtn:hover) — bu yerda `background`
             berilsa, u qisqartma xossa bo'lgani uchun gradientni o'chirardi */
          hoverStyle={{ transform: "translateY(-1px)" }}
        >
          <FaCalculator size={17} />
        </HButton>
        <HButton
          onClick={() => setReportOpen(true)}
          data-tip={s.report}
          aria-label={s.report}
          className={styles.adminBtn}
          baseStyle={{ border: "1px solid var(--tu-glass-border)", color: isDark ? "#E2E8F0" : "#003978", backdropFilter: "var(--tu-glass-blur)", WebkitBackdropFilter: "var(--tu-glass-blur)" }}
          /* Fon hover'i CSS'da (.adminBtn:hover) — bu yerda `background`
             berilsa, u qisqartma xossa bo'lgani uchun gradientni o'chirardi */
          hoverStyle={{ transform: "translateY(-1px)" }}
        >
          <MdReportGmailerrorred size={21} />
        </HButton>
        <NotificationsBell tk={tk} isDark={isDark} s={s} />
        <LangSwitcher lang={lang} onChange={setLang} theme={isDark ? "dark" : "light"} align="right" tip={s.selectLanguage} />
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} tk={tk} label={isDark ? s.dayMode : s.nightMode} />
      </div>

      {calcOpen && (
        <CalculatorModal tk={tk} isDark={isDark} s={s} onClose={() => setCalcOpen(false)} />
      )}

      {reportOpen && (
        <ReportModal tk={tk} isDark={isDark} s={s} onClose={() => setReportOpen(false)} />
      )}

      {ratesOpen && (
        <RatesModal tk={tk} isDark={isDark} s={s} onClose={() => setRatesOpen(false)} />
      )}
    </header>
  );
}
