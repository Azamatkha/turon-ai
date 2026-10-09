import { useState } from "react";
import { createPortal } from "react-dom";
import { useModalA11y } from "../../hooks/useModalA11y";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./SupportModal.module.css";

interface Props {
  S: ChatStaticStrings;
  isDark: boolean;
  onClose: () => void;
}

// Qo'llab-quvvatlash oynasi: yordam telefoni va Telegram bot havolasi.
// Profil menyusidagi "Qo'llab-quvvatlash" bandidan ochiladi.
export default function SupportModal({ S, isDark, onClose }: Props) {
  const modalRef = useModalA11y<HTMLDivElement>(onClose);
  const [copied, setCopied] = useState(false);

  const copyNumber = async () => {
    try {
      await navigator.clipboard.writeText(S.supportNumber);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard ruxsati yo'q — raqam baribir ko'rinib turibdi */
    }
  };

  return createPortal(
    <div
      className={`${styles.overlay} ${isDark ? styles.dark : ""}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-modal-title"
        className={styles.modal}
      >
        <div className={styles.head}>
          <div className={styles.headText}>
            <h2 id="support-modal-title" className={styles.title}>{S.support}</h2>
            <p className={styles.sub}>{S.supportSub}</p>
          </div>
          <button type="button" onClick={onClose} aria-label={S.close} className={styles.closeBtn}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        <div className={styles.rows}>
          {/* Telefon: havola bosilsa qo'ng'iroq ilovasi ochiladi, yonida nusxalash */}
          <div className={styles.row}>
            <span className={styles.icon} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" /></svg>
            </span>
            <div className={styles.rowText}>
              <span className={styles.rowLabel}>{S.supportHint}</span>
              <a href={`tel:${S.supportNumber}`} className={styles.rowValue}>{S.supportNumber}</a>
            </div>
            <button type="button" onClick={() => void copyNumber()} className={styles.copyBtn}>
              {copied ? S.copied : S.copy}
            </button>
            <span className="sr-only" role="status">{copied ? S.copied : ""}</span>
          </div>

          {/* Telegram bot — yangi oynada ochiladi */}
          <a
            href={`https://t.me/${S.supportTelegramBot}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`${styles.row} ${styles.rowLink}`}
          >
            <span className={styles.icon} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2 11 13" /><path d="M22 2 15 22l-4-9-9-4 20-7Z" /></svg>
            </span>
            <div className={styles.rowText}>
              <span className={styles.rowLabel}>{S.supportTelegramLabel}</span>
              <span className={styles.rowValue}>t.me/{S.supportTelegramBot}</span>
            </div>
            <svg className={styles.arrow} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 17 17 7" /><polyline points="8 7 17 7 17 16" /></svg>
          </a>
        </div>
      </div>
    </div>,
    document.body,
  );
}
