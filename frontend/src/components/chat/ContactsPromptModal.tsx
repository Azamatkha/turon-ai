import { useEffect, useState } from "react";
import { updateContacts, type Me } from "../../services/authService";
import {
  IP_NUMBER_MAX_DIGITS,
  UZ_PHONE_PREFIX,
  groupLocalDigits,
  isValidIpNumber,
  isValidLocalPhone,
  phoneLocalDigits,
  toApiPhone,
} from "../../utils/phone";
import type { ChatStaticStrings } from "../../types/i18n";
import { useModalA11y } from "../../hooks/useModalA11y";
// Maydon va tugma stillari Profil oynasi bilan bir xil bo'lsin
import p from "./ProfileModal.module.css";
import styles from "./ContactsPromptModal.module.css";

interface Props {
  S: ChatStaticStrings;
  isDark: boolean;
  me: Me;
  onClose: () => void;
  onSaved: (me: Me) => void;
}

// Oyna o'zi yopilguncha vaqt (5 s juda tez edi — o'qib ulgurilmasdi). Foydalanuvchi oynaga tegsa (bosish, yozish,
// klaviatura) — taymer to'xtaydi va oyna u o'zi yopguncha turadi: yozib
// turgan odamning oynasi qo'lidan "tortib olinmasin".
const AUTO_CLOSE_MS = 10000;

// Kirishda IP raqami yo'q xodimga eslatma: hamkasblar uni topishi uchun
// IP yoki telefon raqamini kiritishni so'raydi. Bittasi yetarli.
export default function ContactsPromptModal({ S, isDark, me, onClose, onSaved }: Props) {
  const [phone, setPhone] = useState(() => phoneLocalDigits(me.phone_number));
  const [ip, setIp] = useState(me.ip_number ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [touched, setTouched] = useState(false);

  const modalRef = useModalA11y<HTMLDivElement>(onClose);

  useEffect(() => {
    if (touched) return;
    const id = window.setTimeout(onClose, AUTO_CLOSE_MS);
    return () => window.clearTimeout(id);
  }, [touched, onClose]);

  const touch = () => {
    if (!touched) setTouched(true);
  };

  const save = async () => {
    if (saving) return;
    if (!phone.trim() && !ip.trim()) {
      setError(S.contactsPromptEmpty);
      return;
    }
    if (!isValidLocalPhone(phone)) {
      setError(S.phoneInvalid);
      return;
    }
    if (!isValidIpNumber(ip)) {
      setError(S.ipNumberInvalid);
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await updateContacts({
        phone_number: toApiPhone(phone),
        ip_number: ip.trim(),
      });
      onSaved(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : S.contactsSaveError);
      setSaving(false);
    }
  };

  return (
    <div
      className={`${p.overlay} ${isDark ? `${p.dark} ${styles.dark}` : ""}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="contacts-prompt-title"
        aria-describedby="contacts-prompt-text"
        className={`${p.modal} ${styles.modal}`}
        onPointerDown={touch}
        onKeyDown={touch}
      >
        {/* Taymer chizig'i — tegilgach yo'qoladi */}
        {!touched && (
          <div className={styles.timer} aria-hidden="true">
            <div className={styles.timerBar} style={{ animationDuration: `${AUTO_CLOSE_MS}ms` }} />
          </div>
        )}

        <div className={styles.head}>
          <span className={styles.icon} aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" /></svg>
          </span>
          <div className={styles.headText}>
            <h2 id="contacts-prompt-title" className={styles.title}>{S.contactsPromptTitle}</h2>
            <p id="contacts-prompt-text" className={styles.text}>{S.contactsPromptText}</p>
          </div>
          <button type="button" onClick={onClose} aria-label={S.close} className={p.closeBtn}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        <form
          className={p.form}
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
          noValidate
        >
          <label className={p.fieldLabel} htmlFor="prompt-ip">{S.infoIpNumber}</label>
          <input
            id="prompt-ip"
            className={p.input}
            value={ip}
            onChange={(e) => {
              touch();
              setIp(e.target.value.replace(/\D/g, "").slice(0, IP_NUMBER_MAX_DIGITS));
            }}
            placeholder="1036"
            inputMode="numeric"
          />

          <label className={p.fieldLabel} htmlFor="prompt-phone">{S.infoPhone}</label>
          <div className={p.phoneField}>
            <span className={p.phonePrefix} aria-hidden="true">{UZ_PHONE_PREFIX}</span>
            <input
              id="prompt-phone"
              className={p.phoneInput}
              value={groupLocalDigits(phone)}
              onChange={(e) => {
                touch();
                setPhone(e.target.value.replace(/\D/g, "").slice(0, 9));
              }}
              placeholder="99 123 45 67"
              inputMode="numeric"
              autoComplete="tel-national"
            />
          </div>

          {error && <div className={p.error} role="alert">{error}</div>}

          <div className={p.actions}>
            <button type="button" onClick={onClose} className={p.secondaryBtn} disabled={saving}>
              {S.contactsPromptLater}
            </button>
            <button type="submit" className={p.primaryBtn} disabled={saving} aria-busy={saving}>
              {S.contactsPromptSave}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
