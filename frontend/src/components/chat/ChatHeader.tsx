import { MdOutlineAdminPanelSettings } from "react-icons/md";
import LangSwitcher from "../LangSwitcher";
import ThemeToggle from "./ThemeToggle";
import HButton from "../common/HButton";
import type { Lang } from "../../types/lang";
import type { ThemeTokens } from "../../types/chat";
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
}

export default function ChatHeader({
  title, lang, setLang, isDark, onToggleTheme, tk, isAdmin, onAdmin, editableTitle, onRenameTitle,
}: ChatHeaderProps) {
  const startEdit = () => {
    if (!editableTitle || !onRenameTitle) return;
    const next = window.prompt("Suhbat nomi", title);
    if (next && next.trim() && next.trim() !== title) onRenameTitle(next.trim());
  };

  return (
    <header className={styles.header} style={{ borderBottom: "1px solid " + tk.headBorder, background: tk.headBg }}>
      <div className={styles.left}>
        <div
          className={styles.title}
          style={{ color: tk.strong, cursor: editableTitle ? "text" : "default" }}
          onDoubleClick={startEdit}
          title={editableTitle ? "Nomini o‘zgartirish uchun ikki marta bosing" : undefined}
        >
          {title}
        </div>
        {editableTitle && (
          <button onClick={startEdit} title="Suhbat nomini tahrirlash" aria-label="Suhbat nomini tahrirlash" className={styles.renameBtn} style={{ color: tk.muted }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" /></svg>
          </button>
        )}
      </div>

      <div className={styles.right}>
        {isAdmin && (
          <HButton
            onClick={() => onAdmin?.()}
            title="Admin panel"
            aria-label="Admin panel"
            className={styles.adminBtn}
            baseStyle={{ background: isDark ? "rgba(255,255,255,.08)" : "#fff", border: "1px solid " + (isDark ? "rgba(255,255,255,.16)" : "#dde2dc"), color: isDark ? "#e8eef2" : "#173f73" }}
            hoverStyle={{ background: isDark ? "rgba(255,255,255,.16)" : "#eef3f6", transform: "translateY(-1px)" }}
          >
            <MdOutlineAdminPanelSettings size={20} />
          </HButton>
        )}
        <LangSwitcher lang={lang} onChange={setLang} theme={isDark ? "dark" : "light"} align="right" />
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} tk={tk} />
      </div>
    </header>
  );
}
