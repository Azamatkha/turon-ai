import { useRef, useState, ChangeEvent, KeyboardEvent } from "react";
import { GrSend } from "react-icons/gr";
import HButton from "../common/HButton";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { ACCENT } from "./theme";
import { DOC_ACCEPT, DOC_MAX_BYTES, isSupportedDoc } from "../../services/documentService";
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
  // Hujjat tahlilchisi: biriktirilgan fayl
  attachment: File | null;
  setAttachment: (f: File | null) => void;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

export default function Composer({ draft, setDraft, canSend, onSend, generating, onStop, placeholder, disclaimer, tk, isDark, s, attachment, setAttachment }: ComposerProps) {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState("");

  const onPickFile = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    // Bir xil faylni qayta tanlash ham onChange bersin
    e.target.value = "";
    if (!f) return;
    if (!isSupportedDoc(f.name)) {
      setFileError(s.fileUnsupported);
      return;
    }
    if (f.size > DOC_MAX_BYTES) {
      setFileError(s.fileTooLarge);
      return;
    }
    setFileError("");
    setAttachment(f);
    taRef.current?.focus();
  };

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
    <div className={styles.wrap} style={{ background: "transparent" }}>
      <div className={styles.inner}>
        {fileError && (
          <div className={styles.fileError} role="alert">
            {fileError}
          </div>
        )}
        {attachment && (
          <div className={styles.chips}>
            <div className={styles.chip} style={{ background: tk.card, border: "1px solid " + tk.cardBorder, color: tk.input }}>
              <span aria-hidden="true">📎</span>
              <span className={styles.chipName} title={attachment.name}>{attachment.name}</span>
              <span className={styles.chipSize}>{fmtSize(attachment.size)}</span>
              <button type="button" className={styles.chipRemove} onClick={() => setAttachment(null)} aria-label={s.removeFile} data-tip={s.removeFile}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </div>
          </div>
        )}
        <div className={styles.bar} style={{ background: tk.card, border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "0 4px 20px rgba(0,0,0,.3)" : "0 4px 20px rgba(14, 27, 66,.07)" }}>
          {/* Ekran o'quvchisi uchun yorliq — placeholder yorliq O'RNINI
              BOSMAYDI: matn terila boshlashi bilan u yo'qoladi va maydon
              "nomsiz" bo'lib qoladi. */}
          <button
            type="button"
            className={styles.attachBtn}
            onClick={() => fileRef.current?.click()}
            disabled={generating}
            aria-label={s.attachFile}
            data-tip={s.attachFile}
          >
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>
          </button>
          <input ref={fileRef} type="file" accept={DOC_ACCEPT} className={styles.fileInput} onChange={onPickFile} tabIndex={-1} aria-hidden="true" />
          <label htmlFor="chat-composer" className="sr-only">
            {placeholder}
          </label>
          <textarea
            id="chat-composer"
            name="message"
            ref={taRef}
            value={draft}
            onChange={onDraft}
            onKeyDown={onKey}
            rows={1}
            placeholder={placeholder}
            className={styles.textarea}
            style={{ color: tk.input }}
            /* Enter = yuborish ekanini ekran o'quvchisi ham aytsin */
            aria-describedby="composer-hint"
          />
          <span id="composer-hint" className="sr-only">
            {s.send} — Enter. {s.newLineHint}
          </span>
          {generating ? (
            <HButton onClick={onStop} data-tip={s.stop} aria-label={s.stop} className={styles.sendBtn} baseStyle={{ background: "#193070", cursor: "pointer" }} hoverStyle={{ transform: "scale(1.08)", background: "#132758" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="#fff" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2.5" /></svg>
            </HButton>
          ) : (
            <HButton
              onClick={send}
              data-tip={s.send}
              aria-label={s.send}
              /* Bo'sh xabarni yuborib bo'lmasligini ekran o'quvchisi ham bilsin —
                 ilgari tugma faqat KO'RINISHI bo'yicha "o'chiq" edi */
              aria-disabled={!canSend}
              className={styles.sendBtn}
              baseStyle={{ background: canSend ? ACCENT : "#CBD5E1", cursor: canSend ? "pointer" : "default" }}
              hoverStyle={canSend ? { transform: "scale(1.08)", background: "#193070" } : {}}
            >
              <GrSend size={16} color="#fff" aria-hidden="true" />
            </HButton>
          )}
        </div>
        <div className={styles.disclaimer} style={{ color: tk.disc }}>{disclaimer}</div>
      </div>
    </div>
  );
}
