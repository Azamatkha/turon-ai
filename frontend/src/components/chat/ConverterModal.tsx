import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MdPictureAsPdf } from "react-icons/md";
import {
  CONVERT_MAX_BYTES,
  ConvertError,
  IMAGE_EXTS,
  MAX_IMAGES,
  OFFICE_EXTS,
  convertToPdf,
  fileExt,
} from "../../services/converterService";
import { ACCENT, PRIMARY_ON_DARK } from "./theme";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ConverterModal.module.css";

interface ConverterModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

const ACCEPT = [...OFFICE_EXTS, ...IMAGE_EXTS].map((e) => "." + e).join(",");
const isImage = (f: File) => IMAGE_EXTS.includes(fileExt(f.name));
const isOffice = (f: File) => OFFICE_EXTS.includes(fileExt(f.name));

const fmtSize = (n: number): string =>
  n >= 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;

/** Natija fayl nomi — birinchi faylning nomi, kengaytmasi .pdf */
const pdfName = (f: File): string => (f.name.replace(/\.[^.]+$/, "") || "file") + ".pdf";

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * PDF konvertor: BITTA Word/Excel/PowerPoint hujjati yoki 1-20 ta rasm ->
 * bitta PDF. Qoidalar backend (src/tools/usecases.py) bilan bir xil — bu
 * yerdagi tekshiruv faqat foydalanuvchi darhol xabar olishi uchun.
 */
export default function ConverterModal({ tk, isDark, s, onClose }: ConverterModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<{ blob: Blob; name: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const accent = isDark ? PRIMARY_ON_DARK : ACCENT;
  const cardBg = "var(--tu-glass-bg-soft)";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, busy]);

  // Yangi fayllarni qo'shadi — qoidaga zid bo'lsa, ro'yxat o'zgarmaydi
  const addFiles = (picked: FileList | null | undefined) => {
    const list = Array.from(picked ?? []);
    if (list.length === 0) return;
    if (list.some((f) => !isImage(f) && !isOffice(f))) {
      setErr(s.convErrType);
      return;
    }
    // Hujjat tanlansa — oldingi tanlov almashtiriladi (hujjat bittadan)
    const next = list.some(isOffice) ? list : [...files.filter(isImage), ...list];
    if (next.some(isOffice) && next.length > 1) {
      setErr(s.convErrMixed);
      return;
    }
    if (next.length > MAX_IMAGES) {
      setErr(s.convErrTooMany);
      return;
    }
    if (next.reduce((sum, f) => sum + f.size, 0) > CONVERT_MAX_BYTES) {
      setErr(s.convErrTooLarge);
      return;
    }
    setErr("");
    setResult(null);
    setFiles(next);
  };

  const removeAt = (i: number) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== i));
    setErr("");
  };

  const reset = () => {
    setFiles([]);
    setResult(null);
    setErr("");
  };

  const submit = async () => {
    if (files.length === 0 || busy) return;
    setBusy(true);
    setErr("");
    try {
      const blob = await convertToPdf(files);
      const name = pdfName(files[0]);
      setResult({ blob, name });
      saveBlob(blob, name);
    } catch (e) {
      // 400 — backend aniq sababni aytadi (masalan "parol bilan himoyalangan"),
      // 413 — hajm; qolgani umumiy xabar
      if (e instanceof ConvertError && e.status === 413) setErr(s.convErrTooLarge);
      else if (e instanceof ConvertError && e.status === 400 && e.message) setErr(e.message);
      else setErr(s.convError);
    } finally {
      setBusy(false);
    }
  };

  const onlyImages = files.length > 0 && files.every(isImage);

  return createPortal(
    <div className={styles.overlay} onClick={() => !busy && onClose()}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={s.convTitle}
      >
        <div className={styles.head}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>
            <MdPictureAsPdf size={21} color={accent} />
            {s.convTitle}
          </div>
          <button className={styles.closeBtn} style={{ color: tk.muted }} onClick={onClose} disabled={busy} aria-label={s.close}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        {result ? (
          <div className={styles.done}>
            <MdPictureAsPdf size={46} color={accent} />
            <div className={styles.doneTitle} style={{ color: tk.strong }}>{s.convDone}</div>
            <div className={styles.doneName} style={{ color: tk.muted }}>
              {result.name} · {fmtSize(result.blob.size)}
            </div>
            <div className={styles.actions}>
              <button type="button" className={styles.secondary} style={{ color: tk.strong, borderColor: tk.cardBorder }} onClick={() => saveBlob(result.blob, result.name)}>
                {s.convDownloadAgain}
              </button>
              <button type="button" className={styles.primary} style={{ background: ACCENT }} onClick={reset}>
                {s.convNew}
              </button>
            </div>
          </div>
        ) : (
          <>
            {files.length === 0 ? (
              <div
                className={styles.drop}
                style={{ borderColor: dragOver ? accent : tk.cardBorder, background: cardBg }}
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  addFiles(e.dataTransfer.files);
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
              >
                <span className={styles.dropTitle} style={{ color: tk.strong }}>{s.convDrop}</span>
                <span className={styles.hint} style={{ color: tk.disc }}>{s.convHint}</span>
              </div>
            ) : (
              <ul className={styles.list}>
                {files.map((f, i) => (
                  <li key={`${f.name}-${i}`} className={styles.item} style={{ background: cardBg, borderColor: tk.cardBorder }}>
                    <span className={styles.ext} style={{ color: accent }}>{fileExt(f.name).toUpperCase()}</span>
                    <span className={styles.itemBody}>
                      <span className={styles.itemName} style={{ color: tk.strong }} title={f.name}>{f.name}</span>
                      <span className={styles.itemSize} style={{ color: tk.muted }}>{fmtSize(f.size)}</span>
                    </span>
                    <button type="button" className={styles.removeBtn} style={{ color: tk.muted }} onClick={() => removeAt(i)} disabled={busy} aria-label={`${s.convRemove}: ${f.name}`} data-tip={s.convRemove}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Rasmlar tanlangan bo'lsa — yana qo'shish mumkin (bitta PDF'ga yig'iladi) */}
            {onlyImages && files.length < MAX_IMAGES && (
              <button type="button" className={styles.addMore} style={{ color: accent }} onClick={() => inputRef.current?.click()} disabled={busy}>
                + {s.convAddMore}
              </button>
            )}

            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ACCEPT}
              className={styles.hidden}
              onChange={(e) => {
                addFiles(e.target.files);
                // Bir xil faylni qayta tanlash ham ishlasin
                e.target.value = "";
              }}
            />

            {err && <div className={styles.error} role="alert">{err}</div>}

            <button
              type="button"
              className={styles.submit}
              style={{ background: ACCENT, opacity: busy || files.length === 0 ? 0.6 : 1 }}
              disabled={busy || files.length === 0}
              onClick={() => void submit()}
              aria-busy={busy}
            >
              {busy ? s.convConverting : s.convSubmit}
            </button>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
