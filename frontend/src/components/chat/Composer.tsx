import { useRef, ChangeEvent, KeyboardEvent } from "react";
import HButton from "../common/HButton";
import type { ThemeTokens } from "../../types/chat";
import { chatStatic } from "../../locales";
import { ACCENT } from "./theme";
import styles from "./Composer.module.css";

interface ComposerProps {
  draft: string;
  setDraft: (v: string) => void;
  canSend: boolean;
  onSend: () => void;
  generating: boolean;
  onStop: () => void;
  placeholder: string;
  disclaimer: string;
  tk: ThemeTokens;
  isDark: boolean;
}

export default function Composer({ draft, setDraft, canSend, onSend, generating, onStop, placeholder, disclaimer, tk, isDark }: ComposerProps) {
  const taRef = useRef<HTMLTextAreaElement>(null);

  const onDraft = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setDraft(e.target.value);
    const ta = taRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    }
  };

  const send = () => {
    onSend();
    const ta = taRef.current;
    if (ta) ta.style.height = "auto";
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className={styles.wrap} style={{ background: `linear-gradient(to top,${tk.bg} 60%,transparent)` }}>
      <div className={styles.inner}>
        <div className={styles.bar} style={{ background: tk.card, border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "0 4px 20px rgba(0,0,0,.3)" : "0 4px 20px rgba(23, 63, 115,.07)" }}>
          <textarea ref={taRef} value={draft} onChange={onDraft} onKeyDown={onKey} rows={1} placeholder={placeholder} className={styles.textarea} style={{ color: tk.input }} />
          {generating ? (
            <HButton onClick={onStop} title={chatStatic.stop} aria-label={chatStatic.stop} className={styles.sendBtn} baseStyle={{ background: "#173f73", cursor: "pointer" }} hoverStyle={{ transform: "scale(1.08)", background: "#0f2c52" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="#fff"><rect x="6" y="6" width="12" height="12" rx="2.5" /></svg>
            </HButton>
          ) : (
            <HButton onClick={send} title={chatStatic.send} aria-label={chatStatic.send} className={styles.sendBtn} baseStyle={{ background: canSend ? ACCENT : "#c4ccc9", cursor: canSend ? "pointer" : "default" }} hoverStyle={canSend ? { transform: "scale(1.08)", background: "#173f73" } : {}}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="6" /><polyline points="6 12 12 6 18 12" /></svg>
            </HButton>
          )}
        </div>
        <div className={styles.disclaimer} style={{ color: tk.disc }}>{disclaimer}</div>
      </div>
    </div>
  );
}
