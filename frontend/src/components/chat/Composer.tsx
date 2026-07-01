import { useRef, ChangeEvent, KeyboardEvent } from "react";
import { GrSend } from "react-icons/gr";
import HButton from "../common/HButton";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
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
  s: ChatStaticStrings;
}

export default function Composer({ draft, setDraft, canSend, onSend, generating, onStop, placeholder, disclaimer, tk, isDark, s }: ComposerProps) {
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
            <HButton onClick={onStop} title={s.stop} aria-label={s.stop} className={styles.sendBtn} baseStyle={{ background: "#173f73", cursor: "pointer" }} hoverStyle={{ transform: "scale(1.08)", background: "#0f2c52" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="#fff"><rect x="6" y="6" width="12" height="12" rx="2.5" /></svg>
            </HButton>
          ) : (
            <HButton onClick={send} title={s.send} aria-label={s.send} className={styles.sendBtn} baseStyle={{ background: canSend ? ACCENT : "#c4ccc9", cursor: canSend ? "pointer" : "default" }} hoverStyle={canSend ? { transform: "scale(1.08)", background: "#173f73" } : {}}>
              <GrSend size={16} color="#fff" />
            </HButton>
          )}
        </div>
        <div className={styles.disclaimer} style={{ color: tk.disc }}>{disclaimer}</div>
      </div>
    </div>
  );
}
