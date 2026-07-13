import HButton from "../common/HButton";
import type { AdminStrings } from "../../types/i18n";
import styles from "./ScrapeModal.module.css";

interface ScrapeModalProps {
  url: string;
  setUrl: (v: string) => void;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: () => void;
  t: AdminStrings;
}

// Havola orqali bilim bazasiga ma'lumot qo'shish oynasi (blur fon, AddUserModal uslubida)
export default function ScrapeModal({ url, setUrl, loading, error, onClose, onSubmit, t: admin }: ScrapeModalProps) {
  return (
    <div onClick={onClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal}>
        <div className={styles.head}>
          <div className={styles.title}>{admin.knowledgeAddModalTitle}</div>
          <HButton onClick={onClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>
        <div className={styles.sub}>{admin.knowledgeAddModalSub}</div>

        <div className={styles.fields}>
          <div>
            <label className={styles.fieldLabel}>{admin.knowledgeUrlLabel}</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSubmit()}
              className={styles.input}
              placeholder={admin.knowledgeUrlPh}
              autoFocus
            />
          </div>
          {error && <div className={styles.errMsg}>{error}</div>}
        </div>

        <HButton onClick={onSubmit} className={styles.submitBtn} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(23, 63, 115,.28)" }}>
          {loading ? <span className={styles.spinner} /> : <span>{admin.knowledgeAdd}</span>}
        </HButton>
      </div>
    </div>
  );
}
