import { Ref, useEffect, useRef, useState } from "react";
import { RiCopperCoinLine, RiMore2Fill } from "react-icons/ri";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { Msg, ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { ACCENT, PRIMARY, PRIMARY_ON_DARK, getSideTokens } from "./theme";
import MessageContent, { toPlainText } from "./MessageContent";
import TypingIndicator from "./TypingIndicator";
import styles from "./MessageArea.module.css";

// Tartib locales'dagi `sugg` massivi bilan BIR XIL bo'lishi shart — ikonka
// indeks bo'yicha olinadi. Yangi taklif qo'shilsa, bu yerga ham ikonka qo'shing.
const suggIcons = ["✦", "✎", "◷", "⊕", "⌂", "☎", "⇄"];

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
  onRegenerate: () => void;
  onEditResend: (id: string, text: string) => void;
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onVote?: (id: string, vote: "up" | "down" | null) => void;
}

type Vote = "up" | "down";

export default function MessageArea({
  scrollRef, isEmpty, hasMessages, greeting, sub, suggestions, onSuggestionClick, rawMsgs, thinking, generating, onRegenerate, onEditResend, tk, isDark, s, onVote,
}: MessageAreaProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Tahrirlanayotgan foydalanuvchi xabari (id) va uning matni
  const [editId, setEditId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  // Qaysi xabar ustidagi "..." menyu ochiq (hover'da chiqadigan menyu)
  const [menuId, setMenuId] = useState<string | null>(null);
  const menuWrapRef = useRef<HTMLDivElement | null>(null);

  // Menyu ochiq bo'lsa — tashqariga bosilganda yopamiz
  useEffect(() => {
    if (!menuId) return;
    const onDown = (e: MouseEvent) => {
      if (!menuWrapRef.current?.contains(e.target as Node)) setMenuId(null);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuId]);

  // Yuklanish (javob kutish) davomida o'tgan vaqtni soniyalab ko'rsatamiz —
  // uzoq kutishda foydalanuvchi jarayon ketayotganini bilib turadi.
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!(thinking || generating)) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => setElapsed((Date.now() - start) / 1000), 200);
    return () => clearInterval(id);
  }, [thinking, generating]);

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
    // role="log" + aria-live="polite" — bot javobi kelganda ekran o'quvchisi
    // uni O'QIYDI. Ilgari bu yo'q edi: ko'zi ojiz foydalanuvchi savol
    // yuborardi va javob kelgan-kelmaganini umuman bilmasdi.
    // "polite" (assertive emas) — foydalanuvchi gapirayotgan bo'lsa,
    // uni bo'lmasdan navbat kutadi.
    <div
      ref={scrollRef}
      className={styles.scrollArea}
      role="log"
      aria-live="polite"
      aria-relevant="additions text"
      aria-label={s.messagesRegion}
    >
      {isEmpty && (
        <div className={styles.emptyState}>
          <div className={styles.greeting} style={{ color: tk.strong, whiteSpace: "pre-line" }}>{greeting}</div>
          <div className={styles.subtext} style={{ color: tk.muted }}>{sub}</div>
          <div className={styles.suggestions}>
            {suggestions.map((label, idx) => (
              <HButton
                key={label}
                onClick={() => onSuggestionClick(label)}
                className={styles.suggestionChip}
                baseStyle={{ border: "1px solid " + tk.cardBorder, color: tk.strong, boxShadow: tk.chipShadow }}
                // Hover'da chegara BREND ko'kiga o'tadi (ilgari kulrang
                // #CBD5E1 edi — shisha fonda qora ramkadek ko'rinardi)
                hoverStyle={{ borderColor: isDark ? "rgba(95,163,214,.55)" : "rgba(11,95,165,.45)", transform: "translateY(-2px)", boxShadow: isDark ? "0 6px 18px rgba(0,0,0,.3)" : "0 4px 14px rgba(0, 57, 120,.1)" }}
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
              // Har bir foydalanuvchi xabari ustida (hover) "..." menyu chiqadi —
              // undan Tahrirlash yoki Qayta yuborish tanlanadi. "Qayta yuborish"
              // shu xabarni (o'sha matn bilan) qaytadan yuboradi — sahifa
              // yangilangach javob tushib qolgan bo'lsa ham qo'l keladi.
              const isEditing = editId === m.id;
              return (
                <div key={m.id} className={`${styles.messageRow} ${styles.messageRowUser}`}>
                  <div className={styles.bubbleColUser}>
                    {isEditing ? (
                      <div className={styles.editBox} style={{ background: tk.card, borderColor: tk.cardBorder }}>
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
                    {!isEditing && (
                      <div className={styles.userMeta}>
                        {/* Bot xabaridagi kabi — ustiga olib borilsa to'liq
                            sana va soat (sekundigacha) ko'rsatiladi. */}
                        {m.time && (
                          <span
                            className={`${styles.msgTimeUser} tip-end`}
                            data-tip={fmtFullTime(m.time)}
                            style={{ color: tk.muted }}
                          >
                            {fmtTime(m.time)}
                          </span>
                        )}
                        {!generating && !thinking && (
                          <div className={styles.msgMenuWrap} ref={menuId === m.id ? menuWrapRef : undefined}>
                            <button
                              onClick={() => setMenuId((cur) => (cur === m.id ? null : m.id))}
                              className={`${styles.msgMenuBtn} ${menuId === m.id ? styles.msgMenuBtnActive : ""}`}
                              aria-label={s.moreOptions}
                              aria-haspopup="menu"
                              aria-expanded={menuId === m.id}
                            >
                              <RiMore2Fill size={15} />
                            </button>
                            {menuId === m.id && (
                              <div role="menu" className={styles.msgMenu} style={{ background: tk.card, border: "1px solid " + tk.cardBorder, color: tk.strong }}>
                                <button role="menuitem" className={styles.msgMenuItem} onClick={() => { setMenuId(null); startEdit(m); }}>
                                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                                  <span>{s.editMessage}</span>
                                </button>
                                <button role="menuitem" className={styles.msgMenuItem} onClick={() => { setMenuId(null); onEditResend(m.id, m.text); }}>
                                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
                                  <span>{s.resend}</span>
                                </button>
                              </div>
                            )}
                          </div>
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
                  <div className={`${styles.bubble} ${styles.bubbleBot}`} style={{ background: tk.card, color: tk.strong, border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "none" : "0 1px 2px rgba(0, 57, 120,.04)" }}>
                    <MessageContent text={m.text} />
                  </div>

                  {showFooter && (
                    <div className={styles.footerRow} style={{ color: tk.muted }}>
                    {showActions && (
                    <div className={styles.actions}>
                      <button onClick={() => copyMsg(m)} className={styles.actBtn} data-tip={copiedId === m.id ? s.copied : s.copy} aria-label={copiedId === m.id ? s.copied : s.copy}>
                        {copiedId === m.id ? (
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
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
                        style={{ color: m.debug.finishReason === "length" ? "#DC2626" : tk.muted }}
                      >
                        <RiCopperCoinLine
                          size={13}
                          style={{ color: m.debug.finishReason === "length" ? "#DC2626" : (isDark ? PRIMARY_ON_DARK : ACCENT) }}
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
                <TypingIndicator color={isDark ? "#5FA3D6" : "#0B5FA5"} />
                {/* Javob kutilayotgan vaqt (soniya) — uzoq kutishda jarayon ketayotgani bilinadi */}
                {elapsed >= 1 && (
                  <span className={styles.tokenMeter} style={{ color: tk.muted, marginLeft: 4 }}>
                    {elapsed.toFixed(1)}s
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
