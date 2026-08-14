import { useEffect, useState } from "react";
import HButton from "../common/HButton";
import type { AdminStrings } from "../../types/i18n";
import {
  getKnowledgeDetail,
  updateKnowledge,
  deleteKnowledge,
  type KnowledgeDetail,
} from "../../services/knowledgeService";
import styles from "./KnowledgeDetailView.module.css";

interface Props {
  title: string;
  onBack: () => void;
  onChanged: () => void; // ro'yxatni yangilash uchun
  t: AdminStrings;
}

// Eski ma'lumotlarda sarlavha har bo'lak boshiga (ba'zan bir necha marta)
// qo'shilib qolgan. Ko'rsatishda va tahrirda bo'lak boshidagi takroriy
// sarlavha satrlarini olib tashlaymiz — bir marta saqlagach baza ham tozalanadi.
function stripTitlePrefix(text: string, title: string): string {
  const t = title.trim();
  if (!t) return text;
  const escaped = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^\\s*(?:${escaped}\\s*\\n+)+`);
  return text.replace(re, "").replace(/^\s+/, "");
}

// Bitta ma'lumotning to'liq sahifasi: ko'rish + tahrirlash + o'chirish.
export default function KnowledgeDetailView({ title, onBack, onChanged, t: admin }: Props) {
  const [detail, setDetail] = useState<KnowledgeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [eTitle, setETitle] = useState("");
  const [eText, setEText] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr(null);
    getKnowledgeDetail(title)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setErr(e instanceof Error ? e.message : admin.knowledgeDetailError))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [title]);

  const startEdit = () => {
    if (!detail) return;
    setETitle(detail.title);
    setEText(detail.chunks.map((c) => stripTitlePrefix(c.text, detail.title)).join("\n\n"));
    setErr(null);
    setEditing(true);
  };

  const save = async () => {
    if (!eTitle.trim() || !eText.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await updateKnowledge(title, eTitle, eText);
      onChanged();
      onBack(); // sarlavha o'zgargan bo'lishi mumkin — ro'yxatga qaytamiz
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    setBusy(true);
    setErr(null);
    try {
      await deleteKnowledge(title);
      onChanged();
      onBack();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeDeleteError);
      setBusy(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <button className={`${styles.backBtn} tu-shiny`} onClick={onBack}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
          {admin.knowledgeBack}
        </button>
        {!editing && detail && (
          <div className={styles.actions}>
            <button className={`${styles.editBtn} tu-shiny`} onClick={startEdit}>{admin.knowledgeEdit}</button>
            <button className={`${styles.delBtn} tu-shiny`} onClick={() => setConfirmDel(true)}>{admin.knowledgeDelete}</button>
          </div>
        )}
      </div>

      {loading ? (
        <div className={styles.state}><span className={styles.spinner} /></div>
      ) : err && !editing ? (
        <div className={styles.errMsg}>{err}</div>
      ) : editing ? (
        <div className={styles.card}>
          <div className={styles.cardTitle}>{admin.knowledgeEditTitle}</div>
          <label className={styles.label}>{admin.uploadTitleLabel}</label>
          <input className={styles.input} value={eTitle} onChange={(e) => setETitle(e.target.value)} />
          <label className={styles.label} style={{ marginTop: 14 }}>{admin.uploadTextLabel}</label>
          <textarea className={styles.textarea} rows={12} value={eText} onChange={(e) => setEText(e.target.value)} />
          {err && <div className={styles.errMsg} style={{ marginTop: 14 }}>{err}</div>}
          <div className={styles.editActions}>
            <button className={styles.cancelBtn} onClick={() => setEditing(false)} disabled={busy}>{admin.knowledgeCancel}</button>
            <HButton onClick={save} className={`${styles.saveBtn} tu-shiny`} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)" }}>
              {busy ? <span className={styles.spinnerSm} /> : admin.knowledgeSave}
            </HButton>
          </div>
        </div>
      ) : detail ? (
        <>
          <div className={styles.title}>{detail.title}</div>
          <div className={styles.chunks}>
            {detail.chunks.map((c) => (
              <div key={c.chunk_index} className={styles.chunk}>
                <div className={styles.chunkLabel}>{admin.knowledgeChunkLabel(c.chunk_index)}</div>
                <div className={styles.chunkText}>{stripTitlePrefix(c.text, detail.title)}</div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {confirmDel && (
        <div className={styles.overlay} onClick={() => setConfirmDel(false)}>
          <div className={styles.confirm} onClick={(e) => e.stopPropagation()}>
            <div className={styles.confirmText}>{admin.knowledgeDeleteConfirm}</div>
            <div className={styles.confirmActions}>
              <button className={styles.cancelBtn} onClick={() => setConfirmDel(false)} disabled={busy}>{admin.knowledgeCancel}</button>
              <button className={`${styles.delConfirmBtn} tu-shiny`} onClick={del} disabled={busy}>
                {busy ? <span className={styles.spinnerSm} /> : admin.knowledgeDelete}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
