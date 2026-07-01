import { Ref, useState } from "react";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { Msg, ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { ACCENT } from "./theme";
import styles from "./MessageArea.module.css";

const suggIcons = ["✦", "✎", "◷", "‹/›"];

// ISO vaqtni "14:05" ko'rinishida ko'rsatadi
function fmtTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

interface MessageAreaProps {
  scrollRef: Ref<HTMLDivElement>;
  isEmpty: boolean;
  hasMessages: boolean;
  greeting: string;
  sub: string;
  suggestions: readonly string[];
  onSuggestionClick: (label: string) => void;
  rawMsgs: Msg[];
  thinking: boolean;
  generating: boolean;
  onRegenerate: () => void;
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onVote?: (id: string, vote: "up" | "down" | null) => void;
}

type Vote = "up" | "down";

export default function MessageArea({
  scrollRef, isEmpty, hasMessages, greeting, sub, suggestions, onSuggestionClick, rawMsgs, thinking, generating, onRegenerate, tk, isDark, s, onVote,
}: MessageAreaProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyMsg = (m: Msg) => {
    navigator.clipboard?.writeText(m.text).then(() => {
      setCopiedId(m.id);
      setTimeout(() => setCopiedId((id) => (id === m.id ? null : id)), 1400);
    });
  };

  // Bosilgan bahoni qayta bossa — bekor qiladi (toggle)
  const vote = (id: string, v: Vote, current: Vote | null | undefined) =>
    onVote?.(id, current === v ? null : v);

  return (
    <div ref={scrollRef} className={styles.scrollArea}>
      {isEmpty && (
        <div className={styles.emptyState}>
          <div className={styles.logoBadge} style={{ color: ACCENT }}><Logo size={64} /></div>
          <div className={styles.greeting} style={{ color: tk.strong, whiteSpace: "pre-line" }}>{greeting}</div>
          <div className={styles.subtext} style={{ color: tk.muted }}>{sub}</div>
          <div className={styles.suggestions}>
            {suggestions.map((label, idx) => (
              <HButton
                key={label}
                onClick={() => onSuggestionClick(label)}
                className={styles.suggestionChip}
                baseStyle={{ background: tk.card, border: "1px solid " + tk.cardBorder, color: tk.strong, boxShadow: tk.chipShadow }}
                hoverStyle={{ background: tk.card, borderColor: isDark ? "rgba(127,179,210,.5)" : "#bcd0e0", transform: "translateY(-2px)", boxShadow: isDark ? "0 6px 18px rgba(0,0,0,.3)" : "0 4px 14px rgba(23, 63, 115,.1)" }}
              >
                <span className={styles.suggestionIcon}>{suggIcons[idx]}</span>
                {label}
              </HButton>
            ))}
          </div>
        </div>
      )}

      {hasMessages && (
        <div className={styles.thread}>
          {rawMsgs.map((m, idx) => {
            const isUser = m.role === "user";
            if (isUser) {
              return (
                <div key={m.id} className={`${styles.messageRow} ${styles.messageRowUser}`}>
                  <div className={styles.bubbleColUser}>
                    <div className={styles.bubbleUser}>{m.text}</div>
                    {m.time && <div className={styles.msgTimeUser} style={{ color: tk.muted }}>{fmtTime(m.time)}</div>}
                  </div>
                </div>
              );
            }

            const isLast = idx === rawMsgs.length - 1;
            // Yozib bo'lgan (yoki to'xtatilgan) bot javobida amallar qatorini ko'rsatamiz
            const showActions = !!m.text && !(generating && isLast);
            const v = m.vote;

            return (
              <div key={m.id} className={`${styles.messageRow} ${styles.messageRowBot}`}>
                <div className={styles.botAvatar}><Logo size={17} /></div>
                <div className={styles.botCol}>
                  <div className={`${styles.bubble} ${styles.bubbleBot}`} style={{ background: tk.card, color: tk.strong, border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "none" : "0 1px 2px rgba(23, 63, 115,.04)" }}>
                    {m.text}
                  </div>

                  {showActions && (
                    <div className={styles.footerRow}>
                    <div className={styles.actions} style={{ color: tk.muted }}>
                      <button onClick={() => copyMsg(m)} className={styles.actBtn} title={copiedId === m.id ? s.copied : s.copy} aria-label={copiedId === m.id ? s.copied : s.copy}>
                        {copiedId === m.id ? (
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1f8a5b" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                        ) : (
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
                        )}
                      </button>

                      <button onClick={() => vote(m.id, "up", v)} className={`${styles.actBtn} ${v === "up" ? styles.actBtnUp : ""}`} title={s.goodResponse} aria-label={s.goodResponse} aria-pressed={v === "up"}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill={v === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12" /><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" /></svg>
                      </button>

                      <button onClick={() => vote(m.id, "down", v)} className={`${styles.actBtn} ${v === "down" ? styles.actBtnDown : ""}`} title={s.badResponse} aria-label={s.badResponse} aria-pressed={v === "down"}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill={v === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2" /><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" /></svg>
                      </button>

                      {isLast && (
                        <button onClick={onRegenerate} className={styles.actBtn} title={s.regenerate} aria-label={s.regenerate}>
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
                        </button>
                      )}
                    </div>
                    {m.time && <span className={styles.msgTimeBot} style={{ color: tk.muted }}>{fmtTime(m.time)}</span>}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {thinking && (
            <div className={styles.typingRow}>
              <div className={styles.botAvatar}><Logo size={17} /></div>
              <div className={styles.typingBubble} style={{ background: tk.card, border: "1px solid " + tk.cardBorder }}>
                {[0, 0.18, 0.36].map((d) => (
                  <span key={d} className={styles.typingDot} style={{ animationDelay: `${d}s` }} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
