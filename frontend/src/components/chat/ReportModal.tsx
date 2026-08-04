import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MdReportGmailerrorred } from "react-icons/md";
import { createReport, type ReportKind } from "../../services/reportService";
import { ACCENT } from "./theme";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ReportModal.module.css";

interface ReportModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

// Backend ham shu turlarni va shu hajmni tekshiradi — bu yerdagisi faqat
// foydalanuvchi darhol xabar olishi uchun.
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024;

export default function ReportModal({ tk, isDark, s, onClose }: ReportModalProps) {
  const [kind, setKind] = useState<ReportKind>("problem");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const cardBg = isDark ? "rgba(255,255,255,.06)" : "#f3f5f8";

  // Object URL faqat preview uchun — komponent yopilganda bo'shatiladi
  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const pickFile = (picked: File | null | undefined) => {
    if (!picked) return;
    if (!ALLOWED_TYPES.includes(picked.type)) {
      setErr(s.reportBadType);
      return;
    }
    if (picked.size > MAX_BYTES) {
      setErr(s.reportTooLarge);
      return;
    }
    setErr("");
    setFile(picked);
  };

  const submit = async () => {
    if (!title.trim() || !text.trim()) {
      setErr(s.reportRequired);
      return;
    }
    setErr("");
    setSending(true);
    try {
      await createReport(kind, title.trim(), text.trim(), file);
      setSent(true);
      // Muvaffaqiyat xabarini ko'rsatib turib, keyin yopamiz
      setTimeout(onClose, 1600);
    } catch (e) {
      setErr(e instanceof Error ? e.message : s.reportError);
    } finally {
      setSending(false);
    }
  };

  const tabs: { id: ReportKind; label: string }[] = [
    { id: "problem", label: s.reportTabProblem },
    { id: "suggestion", label: s.reportTabSuggestion },
  ];

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.scroll}>
          <div className={styles.head}>
            <div className={styles.headTitle} style={{ color: tk.strong }}>
              <MdReportGmailerrorred size={21} color={ACCENT} />
              {s.reportHeading}
            </div>
            <button
              className={styles.closeBtn}
              style={{ color: tk.muted }}
              onClick={onClose}
              aria-label={s.close}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
            </button>
          </div>

          {sent ? (
            <div className={styles.done} style={{ color: tk.strong }}>
              {s.reportSent}
            </div>
          ) : (
            <>
              <div className={styles.tabs} style={{ background: cardBg }}>
                {tabs.map((t) => {
                  const active = kind === t.id;
                  return (
                    <button
                      key={t.id}
                      className={styles.tab}
                      onClick={() => setKind(t.id)}
                      style={{
                        background: active ? tk.card : "transparent",
                        color: active ? ACCENT : tk.muted,
                        boxShadow: active ? "0 2px 8px rgba(9,20,34,.14)" : "none",
                      }}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>

              <div className={styles.field}>
                <label className={styles.label} style={{ color: tk.muted }}>
                  {s.reportTitle}
                </label>
                <input
                  className={styles.input}
                  value={title}
                  maxLength={200}
                  placeholder={s.reportTitlePh}
                  onChange={(e) => setTitle(e.target.value)}
                  style={{ background: cardBg, color: tk.input, borderColor: tk.cardBorder }}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label} style={{ color: tk.muted }}>
                  {s.reportText}
                </label>
                <textarea
                  className={styles.textarea}
                  value={text}
                  maxLength={5000}
                  placeholder={s.reportTextPh}
                  onChange={(e) => setText(e.target.value)}
                  style={{ background: cardBg, color: tk.input, borderColor: tk.cardBorder }}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label} style={{ color: tk.muted }}>
                  {s.reportScreenshot}
                </label>
                <div
                  className={dragOver ? `${styles.drop} ${styles.dropOver}` : styles.drop}
                  style={{ borderColor: dragOver ? ACCENT : tk.cardBorder, background: cardBg }}
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    pickFile(e.dataTransfer.files?.[0]);
                  }}
                >
                  {preview ? (
                    <img className={styles.preview} src={preview} alt="" />
                  ) : (
                    <>
                      <span style={{ color: tk.strong }}>{s.reportScreenshotPick}</span>
                      <span className={styles.hint} style={{ color: tk.disc }}>
                        {s.reportScreenshotHint}
                      </span>
                    </>
                  )}
                </div>
                {file && (
                  <button
                    type="button"
                    className={styles.removeBtn}
                    style={{ color: tk.muted }}
                    onClick={() => setFile(null)}
                  >
                    {s.reportScreenshotRemove}
                  </button>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  className={styles.hidden}
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    pickFile(e.target.files?.[0]);
                    // Bir xil faylni qayta tanlash ham ishlasin
                    e.target.value = "";
                  }}
                />
              </div>

              {err && <div className={styles.error}>{err}</div>}

              <button
                type="button"
                className={styles.submit}
                disabled={sending}
                onClick={() => void submit()}
                style={{ background: ACCENT, opacity: sending ? 0.7 : 1 }}
              >
                {sending ? s.reportSending : s.reportSubmit}
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
