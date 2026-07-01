import { ChangeEvent } from "react";
import HButton from "../common/HButton";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ProfileModal.module.css";

interface ProfileModalProps {
  initial: string;
  userHandle: string;
  pFullName: string;
  setPFullName: (v: string) => void;
  pUsername: string;
  setPUsername: (v: string) => void;
  usernameTaken: boolean;
  usernameOk: boolean;
  pPassword: string;
  setPPassword: (v: string) => void;
  saved: boolean;
  onClose: () => void;
  onSave: () => void;
  onLogout: () => void;
  s: ChatStaticStrings;
  isDark?: boolean;
}

export default function ProfileModal({
  initial, userHandle, pFullName, setPFullName, pUsername, setPUsername,
  usernameTaken, usernameOk, pPassword, setPPassword, saved, onClose, onSave, onLogout, s, isDark,
}: ProfileModalProps) {
  // Dark rejim uchun inline override'lar
  const modalStyle = isDark ? { background: "#15303f", color: "#e8eef2", border: "1px solid rgba(255,255,255,.1)" } : {};
  const inputStyle = isDark ? { background: "#1c3e52", color: "#e8eef2", borderColor: "rgba(255,255,255,.16)" } : {};
  const labelStyle = isDark ? { color: "#aebfc8" } : {};

  return (
    <div onClick={onClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal} style={modalStyle}>
        <div className={styles.head}>
          <div className={styles.headInfo}>
            <div className={styles.avatar}>{initial}</div>
            <div>
              <div className={styles.fullName} style={isDark ? { color: "#e8eef2" } : {}}>{pFullName}</div>
              <div className={styles.handle}>{userHandle}</div>
            </div>
          </div>
          <HButton onClick={onClose} title={s.close} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "#e6eae3", color: "#173f73" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>

        <div className={styles.divider} />

        <div className={styles.fields}>
          <div>
            <label className={styles.fieldLabel} style={labelStyle}>{s.fullName}</label>
            <input className={styles.input} style={inputStyle} value={pFullName} onChange={(e: ChangeEvent<HTMLInputElement>) => setPFullName(e.target.value)} placeholder={s.fullNamePh} />
          </div>
          <div>
            <label className={styles.fieldLabel} style={labelStyle}>{s.username}</label>
            <div className={styles.usernameField} style={inputStyle}>
              <span className={styles.usernamePrefix}>@</span>
              <input className={styles.usernameInput} style={isDark ? { background: "transparent", color: "#e8eef2" } : {}} value={pUsername} onChange={(e: ChangeEvent<HTMLInputElement>) => setPUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ""))} placeholder={s.usernamePh} autoCapitalize="none" />
              {usernameTaken && <span className={styles.takenLabel}>{s.taken}</span>}
              {usernameOk && <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#1f8a5b" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto" }}><polyline points="20 6 9 17 4 12" /></svg>}
            </div>
          </div>
          <div>
            <label className={styles.fieldLabel} style={labelStyle}>{s.newPassword}</label>
            <input className={styles.input} style={inputStyle} value={pPassword} onChange={(e: ChangeEvent<HTMLInputElement>) => setPPassword(e.target.value)} type="password" placeholder={s.newPasswordPh} autoComplete="new-password" />
          </div>
        </div>

        <HButton onClick={onSave} className={`${styles.saveBtn} ${saved ? styles.saveBtnSaved : styles.saveBtnIdle}`} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(23, 63, 115,.28)" }}>
          {saved ? (
            <span className={styles.savedContent}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>{s.saved}
            </span>
          ) : (
            <span>{s.saveChanges}</span>
          )}
        </HButton>

        {/* Qo'llab-quvvatlash: oddiy yordam markazi raqami */}
        <div className={styles.support}>
          <svg className={styles.supportIcon} width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" /></svg>
          <span className={styles.supportHint}>{s.supportHint}</span>
          <span className={styles.supportNumber}>{s.supportNumber}</span>
        </div>

        <HButton onClick={onLogout} className={styles.logoutBtn} baseStyle={{}} hoverStyle={{ background: "#fdeceb", borderColor: "#ecc4c0" }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
          {s.logOut}
        </HButton>
      </div>
    </div>
  );
}
