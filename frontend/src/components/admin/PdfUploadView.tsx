import { useEffect, useRef, useState } from "react";
import {
  getPdfStatus,
  uploadPdf,
  type PdfJobStatus,
} from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./PdfUploadView.module.css";

interface PdfUploadViewProps {
  mounted: boolean;
  t: AdminStrings;
  // Yuklangandan keyin bilim bazasi ro'yxatini yangilash uchun
  onUploaded?: () => void;
}

const POLL_INTERVAL_MS = 3000;

// Hujjat (PDF) yuklash sahifasi. Ish fon rejimida (Celery) bajariladi — OCR +
// LLM tozalash daqiqalab ketadi va korporativ proxy so'rovni 60s da uzardi.
// Yuklash job_id qaytaradi, sahifa holatni har necha soniyada so'rab turadi.
export default function PdfUploadView({ mounted, t: admin, onUploaded }: PdfUploadViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [err, setErr] = useState("");
  const [status, setStatus] = useState<PdfJobStatus | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Poll tsiklini komponent yopilganda to'xtatish uchun
  const cancelledRef = useRef(false);
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // Yuklash yoki ishlash ketayotgan bo'lsa — tugmalar bloklanadi
  const busy =
    status?.state === "queued" || status?.state === "processing";

  const pick = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErr(admin.pdfOnlyPdf);
      return;
    }
    setFile(f);
    setErr("");
    setStatus(null);
  };

  // job tugaguncha (done/error) holatni takror so'raymiz
  const pollUntilDone = async (jobId: string) => {
    while (!cancelledRef.current) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      if (cancelledRef.current) return;
      try {
        const s = await getPdfStatus(jobId);
        if (cancelledRef.current) return;
        setStatus(s);
        if (s.state === "done") {
          onUploaded?.();
          return;
        }
        if (s.state === "error") {
          return;
        }
      } catch (e) {
        setErr(e instanceof Error ? e.message : admin.pdfError);
        setStatus(null);
        return;
      }
    }
  };

  const submit = async () => {
    if (!file || busy) return;
    setErr("");
    setStatus({ state: "queued", message: admin.pdfQueued, title: "", pages: 0, ocr_pages: 0, chunks: 0, error: "" });
    try {
      const { job_id } = await uploadPdf(file, title);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
      await pollUntilDone(job_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.pdfError);
      setStatus(null);
    }
  };

  const sizeMb = file ? (file.size / (1024 * 1024)).toFixed(1) : "0";

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      <div className={styles.card}>
        <div className={styles.title}>{admin.pdfTitle}</div>
        <div className={styles.sub}>{admin.pdfSub}</div>

        <div
          className={`${styles.drop} ${dragOver ? styles.dropOver : ""} ${busy ? styles.dropDisabled : ""}`}
          onClick={() => !busy && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!busy) pick(e.dataTransfer.files?.[0] ?? null);
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
            disabled={busy}
          />
        </div>

        <button className={styles.submitBtn} onClick={submit} disabled={!file || busy}>
          {busy ? (
            <>
              <span className={styles.spinner} />
              <span>{status?.state === "processing" ? admin.pdfProcessing : admin.pdfUploading}</span>
            </>
          ) : (
            <span>{admin.pdfUpload}</span>
          )}
        </button>

        <div className={styles.note}>{admin.pdfSlowNote}</div>

        {err && <div className={styles.errMsg}>{err}</div>}

        {/* Fon ishlash davomida holat, tugagach natija */}
        {status?.state === "processing" && (
          <div className={styles.okMsg}>{status.message || admin.pdfProcessing}</div>
        )}

        {status?.state === "error" && (
          <div className={styles.errMsg}>{status.error || admin.pdfError}</div>
        )}

        {status?.state === "done" && (
          <div className={styles.okMsg}>
            <div className={styles.okTitle}>{status.title}</div>
            <div>{admin.pdfDone(status.pages, status.ocr_pages, status.chunks)}</div>
          </div>
        )}
      </div>
    </div>
  );
}
