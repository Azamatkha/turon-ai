import { useState } from "react";
import HButton from "../common/HButton";
import type { AdminStrings } from "../../types/i18n";
import styles from "./ScrapeModal.module.css";

export interface ScrapeProgress {
  done: number;
  total: number;
}

// Ikki rejim: havola(lar) orqali yoki qo'lda matn kiritib qo'shish
export type AddMode = "url" | "text";

interface ScrapeModalProps {
  url: string;
  setUrl: (v: string) => void;
  // Qo'lda matn rejimi maydonlari
  manTitle: string;
  setManTitle: (v: string) => void;
  manText: string;
  setManText: (v: string) => void;
  loading: boolean;
  error: string | null;
  progress: ScrapeProgress | null;
  onClose: () => void;
  // Har rejim uchun alohida yuborish (AdminPage boshqaradi)
  onSubmitUrl: () => void;
  onSubmitText: () => void;
  t: AdminStrings;
}

// Bilim bazasiga ma'lumot qo'shish oynasi. Ikki tab:
//  - "Havola": bir yoki bir nechta URL — matni avtomatik ajratiladi (scrape).
//  - "Qo'lda matn": admin sarlavha va matnni to'g'ridan-to'g'ri yozadi.
// Ikkalasi ham backendda chunk'larga bo'linib, embed qilinib Qdrant'ga yoziladi.
export default function ScrapeModal({
  url, setUrl, manTitle, setManTitle, manText, setManText,
  loading, error, progress, onClose, onSubmitUrl, onSubmitText, t: admin,
}: ScrapeModalProps) {
  const [mode, setMode] = useState<AddMode>("url");

  // Jarayon ketayotganda oyna tasodifan yopilib qolmasligi kerak
  const handleClose = () => {
    if (loading) return;
    onClose();
  };

  const onSubmit = () => (mode === "url" ? onSubmitUrl() : onSubmitText());

  return (
    <div onClick={handleClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal}>
        <div className={styles.head}>
          <div className={styles.title}>{admin.knowledgeAddModalTitle}</div>
          <HButton onClick={handleClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={loading ? {} : { background: "var(--adm-border)", color: "var(--adm-text-strong)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${mode === "url" ? styles.tabActive : ""}`}
            onClick={() => setMode("url")}
            disabled={loading}
          >
            {admin.knowledgeTabUrl}
          </button>
          <button
            className={`${styles.tab} ${mode === "text" ? styles.tabActive : ""}`}
            onClick={() => setMode("text")}
            disabled={loading}
          >
            {admin.knowledgeTabText}
          </button>
        </div>

        <div className={styles.sub}>
          {mode === "url" ? admin.knowledgeAddModalSub : admin.knowledgeTextSub}
        </div>

        <div className={styles.fields}>
          {mode === "url" ? (
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
          ) : (
            <>
              <div>
                <label className={styles.fieldLabel}>{admin.knowledgeTextTitleLabel}</label>
                <input
                  value={manTitle}
                  onChange={(e) => setManTitle(e.target.value)}
                  className={styles.input}
                  placeholder={admin.knowledgeTextTitlePh}
                  disabled={loading}
                  autoFocus
                />
              </div>
              <div>
                <label className={styles.fieldLabel}>{admin.knowledgeTextBodyLabel}</label>
                <textarea
                  value={manText}
                  onChange={(e) => setManText(e.target.value)}
                  className={styles.textarea}
                  placeholder={admin.knowledgeTextBodyPh}
                  disabled={loading}
                  rows={8}
                />
              </div>
            </>
          )}
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

        <HButton onClick={onSubmit} className={styles.submitBtn} baseStyle={{}} hoverStyle={loading ? {} : { transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(0, 57, 120,.28)" }}>
          {loading ? <span className={styles.spinner} /> : <span>{admin.knowledgeAdd}</span>}
        </HButton>
      </div>
    </div>
  );
}
