import { useRef, useState } from "react";
import { uploadPdf, type PdfUploadResult } from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./PdfUploadView.module.css";

interface PdfUploadViewProps {
  mounted: boolean;
  t: AdminStrings;
  // Yuklangandan keyin bilim bazasi ro'yxatini yangilash uchun
  onUploaded?: () => void;
}

// Hujjat (PDF) yuklash sahifasi. Backend: matn qatlamini o'qiydi, skanerlangan
// sahifalarni OCR qiladi, so'ng AI imzo/muhr shovqinini tozalab bazaga yozadi.
// Bitta fayl — bitta so'rov (keyinchalik API orqali ommaviy yuklanadi).
export default function PdfUploadView({ mounted, t: admin, onUploaded }: PdfUploadViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState<PdfUploadResult | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErr(admin.pdfOnlyPdf);
      return;
    }
    setFile(f);
    setErr("");
    setResult(null);
  };

  const submit = async () => {
    if (!file || loading) return;
    setLoading(true);
    setErr("");
    setResult(null);
    try {
      const res = await uploadPdf(file, title);
      setResult(res);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.pdfError);
    } finally {
      setLoading(false);
    }
  };

  const sizeMb = file ? (file.size / (1024 * 1024)).toFixed(1) : "0";

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      <div className={styles.card}>
        <div className={styles.title}>{admin.pdfTitle}</div>
        <div className={styles.sub}>{admin.pdfSub}</div>

        <div
          className={`${styles.drop} ${dragOver ? styles.dropOver : ""} ${loading ? styles.dropDisabled : ""}`}
          onClick={() => !loading && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            if (!loading) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!loading) pick(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          {file ? (
            <>
              <div className={styles.fileName}>{file.name}</div>
              <div className={styles.fileMeta}>{admin.pdfFileSize(sizeMb)}</div>
            </>
          ) : (
            <div>{admin.pdfDropHint}</div>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className={styles.hidden}
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />

        <div className={styles.field}>
          <label className={styles.fieldLabel}>{admin.pdfTitleLabel}</label>
          <input
            className={styles.input}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={admin.pdfTitlePh}
            disabled={loading}
          />
        </div>

        <button className={styles.submitBtn} onClick={submit} disabled={!file || loading}>
          {loading ? (
            <>
              <span className={styles.spinner} />
              <span>{admin.pdfUploading}</span>
            </>
          ) : (
            <span>{admin.pdfUpload}</span>
          )}
        </button>

        <div className={styles.note}>{admin.pdfSlowNote}</div>

        {err && <div className={styles.errMsg}>{err}</div>}

        {result && (
          <div className={styles.okMsg}>
            <div className={styles.okTitle}>{result.title}</div>
            <div>{admin.pdfDone(result.pages, result.ocr_pages, result.chunks)}</div>
          </div>
        )}
      </div>
    </div>
  );
}
