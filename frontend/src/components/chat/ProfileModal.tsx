import { useEffect, useRef, useState } from "react";
import { fetchMe, type Me } from "../../services/authService";
import type { ChatStaticStrings } from "../../types/i18n";
import { useModalA11y } from "../../hooks/useModalA11y";
import styles from "./ProfileModal.module.css";

interface Props {
  S: ChatStaticStrings;
  isDark: boolean;
  onClose: () => void;
}

// "2001-05-14" -> "14.05.2001"
function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}.${m}.${y}` : iso;
}

// Profil oynasi. Xodim ma'lumotlari FAQAT O'QISH uchun — ular mobil
// verifikatsiyadan va xodimlar bazasidan keladi, o'zgartirishni admin qiladi.
// Kontaktlar (telefon, IP) bu yerda emas: ular menyudagi alohida
// "Kontaktlar" bandida (ContactsPromptModal, mode="edit").
export default function ProfileModal({ S, isDark, onClose }: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    fetchMe().then(setMe).catch(() => setError(true));
  }, []);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  const modalRef = useModalA11y<HTMLDivElement>(onClose);

  const displayName = me?.full_name || me?.username || "";
  const initial = (displayName || "?").charAt(0).toUpperCase();
  const rows: [string, string][] = [
    [S.username, me ? `@${me.username}` : ""],
    [S.infoLastName, me?.last_name ?? ""],
    [S.infoFirstName, me?.first_name ?? ""],
    [S.infoPatronym, me?.patronym ?? ""],
    [S.infoPnfl, me?.pnfl ?? ""],
    [S.infoDocument, [me?.doc_seria, me?.doc_number].filter(Boolean).join(" ")],
    [S.infoBirthDate, formatDate(me?.birth_date)],
    [S.infoDepartment, me?.department ?? ""],
    [S.infoPosition, me?.position ?? ""],
  ];

  return (
    // Faqat qorong'i fonning O'ZIGA bosilganda yopiladi — oyna ichidagi
    // bosish (masalan maydonni belgilab sichqonni tashqariga tortish) yopmaydi
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
        aria-labelledby="profile-modal-title"
        className={styles.modal}
      >
        <div className={styles.head}>
          <div className={styles.avatar}>{initial}</div>
          <div className={styles.headText}>
            <div id="profile-modal-title" className={styles.name}>{displayName || S.profileTitle}</div>
            {me?.position && <div className={styles.meta}>{me.position}</div>}
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label={S.close} className={styles.closeBtn}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        <h2 className={styles.sectionTitle}>{S.employeeInfo}</h2>
        {error ? (
          <div className={styles.error} role="alert">{S.profileLoadError}</div>
        ) : (
          <dl className={styles.list} aria-busy={!me}>
            {rows.map(([label, value]) => (
              <div key={label} className={styles.row}>
                <dt className={styles.label}>{label}</dt>
                <dd className={styles.value}>{me ? value || "—" : "…"}</dd>
              </div>
            ))}
          </dl>
        )}
        <div className={styles.hint}>{S.employeeInfoHint}</div>
      </div>
    </div>
  );
}
