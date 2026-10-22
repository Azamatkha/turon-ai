import { useEffect, useRef, useState } from "react";
import {
  deleteGuide,
  listGuides,
  renameGuide,
  uploadGuide,
  type EdoGuide,
} from "../../services/guideService";
import type { AdminStrings } from "../../types/i18n";
import upload from "./PdfUploadView.module.css";
import styles from "./GuidesAdminView.module.css";

interface GuidesAdminViewProps {
  mounted: boolean;
  t: AdminStrings;
}

const MAX_BYTES = 200 * 1024 * 1024;

const fmtMb = (bytes: number) => (bytes / (1024 * 1024)).toFixed(1);

// EDO yo'riqnomalari: admin MP4 video yuklaydi (sarlavha bilan), ro'yxatda
// nomini o'zgartiradi yoki o'chiradi. Video bo'laklab yuklanadi, progress
// ko'rsatiladi va istalgan payt bekor qilish mumkin.
export default function GuidesAdminView({ mounted, t: admin }: GuidesAdminViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [err, setErr] = useState("");
  const [okTitle, setOkTitle] = useState("");

  const [items, setItems] = useState<EdoGuide[]>([]);
  const [listFailed, setListFailed] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const uploading = progress !== null;

  const reload = () =>
    listGuides()
      .then((list) => {
        setItems(list);
        setListFailed(false);
      })
      .catch(() => setListFailed(true));

  useEffect(() => {
    void reload();
    // Sahifadan chiqilsa — davom etayotgan yuklash to'xtatiladi
    return () => abortRef.current?.abort();
  }, []);

  const pick = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".mp4")) {
      setErr(admin.guidesOnlyMp4);
      return;
    }
    if (f.size > MAX_BYTES) {
      setErr(admin.guidesTooLarge);
      return;
    }
    setFile(f);
    setErr("");
    setOkTitle("");
    // Sarlavha bo'sh bo'lsa — fayl nomidan taklif
    if (!title.trim()) setTitle(f.name.replace(/\.mp4$/i, ""));
  };

  const submit = async () => {
    if (!file || uploading) return;
    if (!title.trim()) {
      setErr(admin.guidesTitleRequired);
      return;
    }
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setErr("");
    setOkTitle("");
    setProgress(0);
    try {
      const guide = await uploadGuide(file, title, setProgress, ctrl.signal);
      setOkTitle(guide.title);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
      void reload();
    } catch (e) {
      if (!ctrl.signal.aborted) setErr(e instanceof Error ? e.message : admin.guidesError);
    } finally {
      setProgress(null);
      abortRef.current = null;
    }
  };

  const cancel = () => abortRef.current?.abort();

  const saveTitle = async (id: string) => {
    const next = editTitle.trim();
    if (!next) return;
    setBusyId(id);
    try {
      const updated = await renameGuide(id, next);
      setItems((list) => list.map((g) => (g.id === id ? updated : g)));
      setEditId(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.guidesError);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (id: string) => {
    setBusyId(id);
    try {
      await deleteGuide(id);
      setItems((list) => list.filter((g) => g.id !== id));
      setConfirmId(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.guidesError);
    } finally {
      setBusyId(null);
    }
  };

  const percent = Math.round((progress ?? 0) * 100);

  return (
    <div className={`${upload.wrap} ${styles.wrap} ${mounted ? upload.in : ""}`}>
      <div className={upload.card}>
        <div className={upload.title}>{admin.guidesUploadTitle}</div>
        <div className={upload.sub}>{admin.guidesUploadSub}</div>

        <div
          className={`${upload.drop} ${dragOver ? upload.dropOver : ""} ${uploading ? upload.dropDisabled : ""}`}
          role="button"
          tabIndex={uploading ? -1 : 0}
          aria-label={admin.guidesDropHint}
          onClick={() => !uploading && inputRef.current?.click()}
          onKeyDown={(e) => {
            if (!uploading && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            if (!uploading) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!uploading) pick(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="2" y="5" width="15" height="14" rx="2" />
            <path d="m17 10 5-3v10l-5-3" />
          </svg>
          {file ? (
            <>
              <div className={upload.fileName}>{file.name}</div>
              <div className={upload.fileMeta}>{fmtMb(file.size)} MB</div>
            </>
          ) : (
            <div>{admin.guidesDropHint}</div>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="video/mp4,.mp4"
          className={upload.hidden}
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />

        <div className={upload.field}>
          <label className={upload.fieldLabel} htmlFor="guide-title">{admin.guidesTitleLabel}</label>
          <input
            id="guide-title"
            className={upload.input}
            value={title}
            maxLength={200}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={admin.guidesTitlePh}
            disabled={uploading}
          />
        </div>

        {uploading ? (
          <div className={styles.progressRow}>
            <div
              className={styles.progress}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label={admin.guidesUploading}
            >
              <div className={styles.progressBar} style={{ width: `${percent}%` }} />
            </div>
            <span className={styles.progressText}>{percent}%</span>
            <button type="button" className={styles.cancelBtn} onClick={cancel}>
              {admin.knowledgeCancel}
            </button>
          </div>
        ) : (
          <button className={`${upload.submitBtn} tu-shiny`} onClick={submit} disabled={!file}>
            <span>{admin.guidesUpload}</span>
          </button>
        )}

        {err && <div className={upload.errMsg} role="alert">{err}</div>}
        {okTitle && (
          <div className={upload.okMsg} role="status">
            <div className={upload.okTitle}>{okTitle}</div>
            <div>{admin.guidesUploaded}</div>
          </div>
        )}
      </div>

      <div className={`${upload.card} ${styles.listCard}`}>
        <div className={upload.title}>
          {admin.guidesListTitle} <span className={styles.count}>{items.length}</span>
        </div>
        {listFailed ? (
          <div className={upload.errMsg}>{admin.guidesError}</div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>{admin.guidesEmpty}</div>
        ) : (
          <ul className={styles.list}>
            {items.map((g) => (
              <li key={g.id} className={styles.row}>
                {editId === g.id ? (
                  <input
                    className={`${upload.input} ${styles.editInput}`}
                    value={editTitle}
                    maxLength={200}
                    autoFocus
                    aria-label={admin.guidesTitleLabel}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void saveTitle(g.id);
                      if (e.key === "Escape") setEditId(null);
                    }}
                  />
                ) : (
                  <div className={styles.rowMain}>
                    <div className={styles.rowTitle}>{g.title}</div>
                    <div className={styles.rowMeta}>
                      {fmtMb(g.size_bytes)} MB · {new Date(g.created_at).toLocaleDateString("ru-RU")}
                    </div>
                  </div>
                )}

                <div className={styles.actions}>
                  {editId === g.id ? (
                    <>
                      <button type="button" className={styles.btn} disabled={busyId === g.id} onClick={() => void saveTitle(g.id)}>
                        {admin.guidesSave}
                      </button>
                      <button type="button" className={styles.btnGhost} onClick={() => setEditId(null)}>
                        {admin.knowledgeCancel}
                      </button>
                    </>
                  ) : confirmId === g.id ? (
                    <>
                      <span className={styles.confirmText}>{admin.guidesDeleteConfirm}</span>
                      <button type="button" className={styles.btnDanger} disabled={busyId === g.id} onClick={() => void remove(g.id)}>
                        {admin.knowledgeDelete}
                      </button>
                      <button type="button" className={styles.btnGhost} onClick={() => setConfirmId(null)}>
                        {admin.knowledgeCancel}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className={styles.btnGhost}
                        onClick={() => {
                          setEditId(g.id);
                          setEditTitle(g.title);
                          setConfirmId(null);
                        }}
                      >
                        {admin.guidesRename}
                      </button>
                      <button
                        type="button"
                        className={styles.btnGhostDanger}
                        onClick={() => {
                          setConfirmId(g.id);
                          setEditId(null);
                        }}
                      >
                        {admin.knowledgeDelete}
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
