import HButton from "../common/HButton";
import type { AdminStrings } from "../../types/i18n";
import styles from "./ScrapeModal.module.css";

export interface ScrapeProgress {
  done: number;
  total: number;
}

interface ScrapeModalProps {
  url: string;
  setUrl: (v: string) => void;
  loading: boolean;
  error: string | null;
  progress: ScrapeProgress | null;
  onClose: () => void;
  onSubmit: () => void;
  t: AdminStrings;
}

// Havola(lar) orqali bilim bazasiga ma'lumot qo'shish oynasi (blur fon, AddUserModal uslubida).
// Bir nechta havola bo'lsa — har biri alohida qatorda, ketma-ket (for loop) qo'shiladi.
export default function ScrapeModal({ url, setUrl, loading, error, progress, onClose, onSubmit, t: admin }: ScrapeModalProps) {
  // Jarayon ketayotganda oyna tasodifan yopilib qolmasligi kerak
  const handleClose = () => {
    if (loading) return;
    onClose();
  };

  return (
    <div onClick={handleClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal}>
        <div className={styles.head}>
          <div className={styles.title}>{admin.knowledgeAddModalTitle}</div>
          <HButton onClick={handleClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={loading ? {} : { background: "var(--adm-border)", color: "var(--adm-text-strong)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>
        <div className={styles.sub}>{admin.knowledgeAddModalSub}</div>

        <div className={styles.fields}>
          <div>
            <label className={styles.fieldLabel}>{admin.knowledgeUrlLabel}</label>
            <textarea
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className={styles.textarea}
              placeholder={admin.knowledgeUrlPh}
              disabled={loading}
              autoFocus
              rows={6}
            />
          </div>
          {error && <div className={styles.errMsg}>{error}</div>}
          {progress && (
            <div className={styles.progressWrap}>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}
                />
              </div>
              <div className={styles.progressLabel}>{admin.knowledgeBulkProgress(progress.done, progress.total)}</div>
            </div>
          )}
        </div>

        <HButton onClick={onSubmit} className={styles.submitBtn} baseStyle={{}} hoverStyle={loading ? {} : { transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(23, 63, 115,.28)" }}>
          {loading ? <span className={styles.spinner} /> : <span>{admin.knowledgeAdd}</span>}
        </HButton>
      </div>
    </div>
  );
}
