import { Ref, useState } from "react";
import { RiCopperCoinLine } from "react-icons/ri";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { Msg, ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { ACCENT, PRIMARY, PRIMARY_ON_DARK, getSideTokens } from "./theme";
import MessageContent, { toPlainText } from "./MessageContent";
import TypingIndicator from "./TypingIndicator";
import styles from "./MessageArea.module.css";

const suggIcons = ["✦", "✎", "◷", "‹/›"];

// ISO vaqtni "14:05" ko'rinishida ko'rsatadi
function fmtTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

// Hover hint uchun to'liq sana-vaqt: "13.07.2026 9:41:32"
function fmtFullTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit", hour12: false });
  return `${day}.${month}.${d.getFullYear()} ${time}`;
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
  liveTokens: number;
  onRegenerate: () => void;
  onResend: () => void;
  onEditResend: (id: string, text: string) => void;
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onVote?: (id: string, vote: "up" | "down" | null) => void;
}

type Vote = "up" | "down";

export default function MessageArea({
  scrollRef, isEmpty, hasMessages, greeting, sub, suggestions, onSuggestionClick, rawMsgs, thinking, generating, liveTokens, onRegenerate, onResend, onEditResend, tk, isDark, s, onVote,
}: MessageAreaProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Tahrirlanayotgan foydalanuvchi xabari (id) va uning matni
  const [editId, setEditId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const startEdit = (m: Msg) => { setEditId(m.id); setEditText(m.text); };
  const cancelEdit = () => { setEditId(null); setEditText(""); };
  const saveEdit = (id: string) => {
    const t = editText.trim();
    if (t) onEditResend(id, t);
    cancelEdit();
  };
  // Foydalanuvchi xabari foni sidebar rangi bilan bir xil (light mode uchun so'ralgan)
  const side = getSideTokens(isDark);

  const copyMsg = (m: Msg) => {
    navigator.clipboard?.writeText(toPlainText(m.text)).then(() => {
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
          <div className={styles.logoBadge} style={{ color: isDark ? PRIMARY_ON_DARK : PRIMARY }}><Logo size={64} /></div>
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
              // Oxirgi xabar shu (user) bo'lib, unga hali javob kelmagan bo'lsa —
              // sahifa yangilanganda (refresh) javob abadiy tushib qolgan bo'ladi
              // (assistant javobi faqat "typing" animatsiyasi tugagach saqlanadi).
              // Shunday holatda qayta yuborish tugmasini ko'rsatamiz.
              const isDangling = idx === rawMsgs.length - 1 && !thinking && !generating;
              const isEditing = editId === m.id;
              return (
                <div key={m.id} className={`${styles.messageRow} ${styles.messageRowUser}`}>
                  <div className={styles.bubbleColUser}>
                    {isEditing ? (
                      <div className={styles.editBox} style={{ background: side.bg, borderColor: tk.cardBorder }}>
                        <textarea
                          className={styles.editArea}
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); saveEdit(m.id); }
                            if (e.key === "Escape") cancelEdit();
                          }}
                          autoFocus
                          rows={Math.min(6, editText.split("\n").length)}
                          style={{ color: tk.strong }}
                        />
                        <div className={styles.editActions}>
                          <button onClick={cancelEdit} className={styles.editBtnGhost} style={{ color: tk.muted }}>{s.cancelEdit}</button>
                          <button onClick={() => saveEdit(m.id)} className={styles.editBtnPrimary} disabled={!editText.trim()}>{s.saveEdit}</button>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.bubbleUser} style={{ background: side.bg }}>{m.text}</div>
                    )}
                    {!isEditing && m.time && <div className={styles.msgTimeUser} style={{ color: tk.muted }}>{fmtTime(m.time)}</div>}
                    {!isEditing && !generating && !thinking && (
                      <div className={styles.userActions}>
                        <button onClick={() => startEdit(m)} className={styles.resendBtn} aria-label={s.editMessage}>
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                          {s.editMessage}
                        </button>
                        {isDangling && (
                          <button onClick={onResend} className={styles.resendBtn} aria-label={s.resend}>
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
                            {s.resend}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            const isLast = idx === rawMsgs.length - 1;
            const isStreaming = generating && isLast;
            // Amal tugmalari javob tugagach ko'rinadi; token hisoblagichi esa yozilish
            // paytida ham ko'rinadi (real vaqtda 1,2,3... sanab boradi).
            const showActions = !!m.text && !isStreaming;
            // Streaming paytida token yuklanish indikatorida ko'rsatiladi — bu yerda
            // faqat javob tugagach (yakuniy aniq son) ko'rsatamiz (takror bo'lmasin).
            const hasTokens = !!m.debug && !!m.text && m.debug.completionTokens > 0 && !isStreaming;
            const showFooter = showActions || hasTokens;
            const v = m.vote;

            return (
              <div key={m.id} className={`${styles.messageRow} ${styles.messageRowBot}`}>
                <div className={styles.botAvatar}><Logo size={17} /></div>
                <div className={styles.botCol}>
                  <div className={`${styles.bubble} ${styles.bubbleBot}`} style={{ background: tk.card, color: tk.strong, border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "none" : "0 1px 2px rgba(23, 63, 115,.04)" }}>
                    <MessageContent text={m.text} />
                  </div>

                  {showFooter && (
                    <div className={styles.footerRow} style={{ color: tk.muted }}>
                    {showActions && (
                    <div className={styles.actions}>
                      <button onClick={() => copyMsg(m)} className={styles.actBtn} data-tip={copiedId === m.id ? s.copied : s.copy} aria-label={copiedId === m.id ? s.copied : s.copy}>
                        {copiedId === m.id ? (
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1f8a5b" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                        ) : (
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
                        )}
                      </button>

                      <button onClick={() => vote(m.id, "up", v)} className={`${styles.actBtn} ${v === "up" ? styles.actBtnUp : ""}`} data-tip={s.goodResponse} aria-label={s.goodResponse} aria-pressed={v === "up"}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill={v === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12" /><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" /></svg>
                      </button>

                      <button onClick={() => vote(m.id, "down", v)} className={`${styles.actBtn} ${v === "down" ? styles.actBtnDown : ""}`} data-tip={s.badResponse} aria-label={s.badResponse} aria-pressed={v === "down"}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill={v === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2" /><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" /></svg>
                      </button>

                      {isLast && (
                        <button onClick={onRegenerate} className={styles.actBtn} data-tip={s.regenerate} aria-label={s.regenerate}>
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
                        </button>
                      )}
                    </div>
                    )}
                    {/* Real-time token hisoblagichi — javob yozilishi bilan son o'zgaradi
                        (streaming paytida ham). finishReason === "length" bo'lsa — qizil. */}
                    {m.debug && !!m.text && m.debug.completionTokens > 0 && (
                      <span
                        className={styles.tokenMeter}
                        style={{ color: m.debug.finishReason === "length" ? "#c0392b" : tk.muted }}
                      >
                        <RiCopperCoinLine
                          size={13}
                          style={{ color: m.debug.finishReason === "length" ? "#c0392b" : ACCENT }}
                        />
                        {m.debug.completionTokens} token
                      </span>
                    )}
                    {!isStreaming && m.time && (
                      <span className={`${styles.msgTimeBot} tip-end`} data-tip={fmtFullTime(m.time)}>
                        {fmtTime(m.time)}
                      </span>
                    )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {(thinking || generating) && (
            <div className={styles.typingRow}>
              <div className={styles.botAvatar}><Logo size={17} /></div>
              <div className={styles.typingBubble} style={{ background: tk.card, border: "1px solid " + tk.cardBorder }}>
                <TypingIndicator color={isDark ? "#7fb3d2" : "#3a7ca5"} />
                {/* Javob yozilayotgan paytda real vaqtda o'sib boruvchi token soni */}
                {liveTokens > 0 && (
                  <span className={styles.tokenMeter} style={{ color: tk.muted, marginLeft: 4 }}>
                    <RiCopperCoinLine size={13} style={{ color: ACCENT }} />
                    {liveTokens} token
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
