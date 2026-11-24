import { useCallback, useEffect, useRef, useState } from "react";
import { getPdfJob, listPdfJobs, uploadPdf, type PdfJob } from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./PdfUploadView.module.css";

interface PdfUploadViewProps {
  mounted: boolean;
  t: AdminStrings;
  // Yuklangandan keyin bilim bazasi ro'yxatini yangilash uchun
  onUploaded?: () => void;
}

// Fon ishi holati shu oraliqda so'raladi
const POLL_MS = 3000;

const isActive = (j: PdfJob) => j.status === "queued" || j.status === "running";

function JobStatus({ job, admin }: { job: PdfJob; admin: AdminStrings }) {
  if (job.status === "done" && job.result) {
    return <div>{admin.pdfDone(job.result.pages, job.result.ocr_pages, job.result.chunks)}</div>;
  }
  if (job.status === "failed") {
    return <div className={styles.jobError}>{job.error || admin.pdfError}</div>;
  }
  let text = admin.pdfStageQueued;
  if (job.status === "running") {
    if (job.stage === "reading") text = admin.pdfStageReading(job.done, job.total);
    else if (job.stage === "cleaning") text = admin.pdfStageCleaning(job.done, job.total);
    else if (job.stage === "saving") text = admin.pdfStageSaving;
    else text = admin.pdfUploading;
  }
  const pct = job.total > 0 ? Math.min(100, (job.done / job.total) * 100) : 0;
  return (
    <>
      <div className={styles.jobLive}>
        <span className={styles.spinnerDark} />
        <span>{text}</span>
      </div>
      {job.total > 0 && (
        <div className={styles.bar}>
          <div className={styles.barFill} style={{ width: `${pct}%` }} />
        </div>
      )}
    </>
  );
}

// Hujjat (PDF) yuklash sahifasi. Fayl yuborilgach server darhol javob beradi,
// o'qish (model/OCR), tozalash va bazaga yozish FONDA bajariladi — sahifa
// holatni so'rab turadi. Sahifa yopilsa ham ish davom etadi, qayta ochilganda
// oxirgi yuklashlar ro'yxati yana ko'rinadi.
export default function PdfUploadView({ mounted, t: admin, onUploaded }: PdfUploadViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const [jobs, setJobs] = useState<PdfJob[]>([]);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    listPdfJobs()
      .then(setJobs)
      .catch(() => {
        // ro'yxat bo'lmasa ham yuklash ishlayveradi
      });
  }, []);

  // Faol ishlar holatini so'rab turamiz; biri tugasa — baza ro'yxati yangilanadi
  const anyActive = jobs.some(isActive);
  const refresh = useCallback(async () => {
    const active = jobs.filter(isActive);
    const fresh = await Promise.all(active.map((j) => getPdfJob(j.id).catch(() => j)));
    const byId = new Map(fresh.map((j) => [j.id, j]));
    if (fresh.some((j) => j.status === "done")) onUploaded?.();
    setJobs((prev) => prev.map((j) => byId.get(j.id) ?? j));
  }, [jobs, onUploaded]);

  useEffect(() => {
    if (!anyActive) return;
    const id = window.setTimeout(() => void refresh(), POLL_MS);
    return () => window.clearTimeout(id);
  }, [anyActive, refresh]);

  const pick = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErr(admin.pdfOnlyPdf);
      return;
    }
    setFile(f);
    setErr("");
  };

  const submit = async () => {
    if (!file || sending) return;
    setSending(true);
    setErr("");
    try {
      const job = await uploadPdf(file, title);
      setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)]);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.pdfError);
    } finally {
      setSending(false);
    }
  };

  const sizeMb = file ? (file.size / (1024 * 1024)).toFixed(1) : "0";

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      <div className={styles.card}>
        <div className={styles.title}>{admin.pdfTitle}</div>
        <div className={styles.sub}>{admin.pdfSub}</div>

        <div
          className={`${styles.drop} ${dragOver ? styles.dropOver : ""} ${sending ? styles.dropDisabled : ""}`}
          onClick={() => !sending && inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            if (!sending) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!sending) pick(e.dataTransfer.files?.[0] ?? null);
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
            disabled={sending}
          />
        </div>

        <button className={`${styles.submitBtn} tu-shiny`} onClick={submit} disabled={!file || sending}>
          {sending ? (
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

        {jobs.length > 0 && (
          <div className={styles.jobs}>
            <div className={styles.jobsTitle}>{admin.pdfJobsTitle}</div>
            {jobs.map((job) => (
              <div key={job.id} className={styles.okMsg}>
                <div className={styles.okTitle}>{job.result?.title || job.title || job.filename}</div>
                {(job.result?.title || job.title) && <div className={styles.jobFile}>{job.filename}</div>}
                <JobStatus job={job} admin={admin} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
