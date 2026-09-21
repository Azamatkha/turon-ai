import { useEffect, useRef, useState } from "react";
import { fetchMe, updateContacts, type Me } from "../../services/authService";
import {
  IP_NUMBER_MAX_DIGITS,
  UZ_PHONE_PREFIX,
  formatPhone,
  groupLocalDigits,
  isValidIpNumber,
  isValidLocalPhone,
  phoneLocalDigits,
  toApiPhone,
} from "../../utils/phone";
import type { ChatStaticStrings } from "../../types/i18n";
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
// Kontaktlarni (telefon, IP raqam) esa foydalanuvchi O'ZI kiritadi — ikkalasi
// ham ixtiyoriy.
export default function ProfileModal({ S, isDark, onClose }: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Kontaktlarni tahrirlash holati
  const [editing, setEditing] = useState(false);
  const [phone, setPhone] = useState(""); // faqat +998 dan keyingi 9 ta raqam
  const [ip, setIp] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchMe().then(setMe).catch(() => setError(true));
  }, []);

  // Escape: tahrirlanayotgan bo'lsa — tahrirni bekor qiladi, aks holda oynani yopadi
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (editing) setEditing(false);
      else onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, editing]);

  const startEdit = () => {
    setPhone(phoneLocalDigits(me?.phone_number));
    setIp(me?.ip_number ?? "");
    setSaveError("");
    setEditing(true);
  };

  const saveContacts = async () => {
    if (saving) return;
    if (!isValidLocalPhone(phone)) {
      setSaveError(S.phoneInvalid);
      return;
    }
    if (!isValidIpNumber(ip)) {
      setSaveError(S.ipNumberInvalid);
      return;
    }
    setSaving(true);
    setSaveError("");
    try {
      // Bo'sh maydon backendda raqamni o'chiradi
      const updated = await updateContacts({
        phone_number: toApiPhone(phone),
        ip_number: ip.trim(),
      });
      setMe(updated);
      setEditing(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : S.contactsSaveError);
    } finally {
      setSaving(false);
    }
  };

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

        {/* Kontaktlar — foydalanuvchi o'zi kiritadi (ixtiyoriy) */}
        {me && (
          <section className={styles.contacts} aria-labelledby="profile-contacts-title">
            <div className={styles.contactsHead}>
              <h2 id="profile-contacts-title" className={styles.sectionTitle}>{S.contactsTitle}</h2>
              {!editing && (
                <button type="button" onClick={startEdit} className={styles.linkBtn}>
                  {saved ? S.saved : S.contactsEdit}
                </button>
              )}
            </div>

            {!editing ? (
              <dl className={styles.list}>
                <div className={styles.row}>
                  <dt className={styles.label}>{S.infoPhone}</dt>
                  <dd className={styles.value}>{formatPhone(me.phone_number) || "—"}</dd>
                </div>
                <div className={styles.row}>
                  <dt className={styles.label}>{S.infoIpNumber}</dt>
                  <dd className={styles.value}>{me.ip_number || "—"}</dd>
                </div>
              </dl>
            ) : (
              <div className={styles.form}>
                <label className={styles.fieldLabel} htmlFor="profile-phone">{S.infoPhone}</label>
                <div className={styles.phoneField}>
                  <span className={styles.phonePrefix} aria-hidden="true">{UZ_PHONE_PREFIX}</span>
                  <input
                    id="profile-phone"
                    className={styles.phoneInput}
                    value={groupLocalDigits(phone)}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 9))}
                    placeholder="99 123 45 67"
                    inputMode="numeric"
                    autoComplete="tel-national"
                  />
                </div>

                <label className={styles.fieldLabel} htmlFor="profile-ip">{S.infoIpNumber}</label>
                <input
                  id="profile-ip"
                  className={styles.input}
                  value={ip}
                  onChange={(e) => setIp(e.target.value.replace(/\D/g, "").slice(0, IP_NUMBER_MAX_DIGITS))}
                  placeholder="1036"
                  inputMode="numeric"
                />

                <div className={styles.hint}>{S.contactsHint}</div>
                {saveError && <div className={styles.error} role="alert">{saveError}</div>}

                <div className={styles.actions}>
                  <button type="button" onClick={() => setEditing(false)} className={styles.secondaryBtn} disabled={saving}>
                    {S.cancelEdit}
                  </button>
                  <button type="button" onClick={saveContacts} className={styles.primaryBtn} disabled={saving} aria-busy={saving}>
                    {S.saveChanges}
                  </button>
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
