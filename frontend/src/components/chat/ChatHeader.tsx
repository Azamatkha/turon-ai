import LangSwitcher from "../LangSwitcher";
import ThemeToggle from "./ThemeToggle";
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
}

export default function ChatHeader({ title, lang, setLang, isDark, onToggleTheme, tk }: ChatHeaderProps) {
  return (
    <header className={styles.header} style={{ borderBottom: "1px solid " + tk.headBorder, background: tk.headBg }}>
      <div className={styles.left}>
        <div className={styles.title} style={{ color: tk.strong }}>{title}</div>
      </div>

      <div className={styles.right}>
        <LangSwitcher lang={lang} onChange={setLang} theme={isDark ? "dark" : "light"} align="right" />
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} tk={tk} />
      </div>
    </header>
  );
}
