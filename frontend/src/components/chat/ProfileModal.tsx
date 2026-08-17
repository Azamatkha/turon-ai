import { ChangeEvent, useState } from "react";
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
  pCurrentPassword: string;
  setPCurrentPassword: (v: string) => void;
  pPassword: string;
  setPPassword: (v: string) => void;
  pConfirmPassword: string;
  setPConfirmPassword: (v: string) => void;
  error: string;
  saved: boolean;
  saving?: boolean;
  onClose: () => void;
  onSave: () => void;
  onLogout: () => void;
  s: ChatStaticStrings;
  isDark?: boolean;
}

export default function ProfileModal({
  initial, userHandle, pFullName, setPFullName, pUsername, setPUsername,
  pCurrentPassword, setPCurrentPassword, pPassword, setPPassword, pConfirmPassword, setPConfirmPassword,
  error, saved, saving, onClose, onSave, onLogout, s, isDark,
}: ProfileModalProps) {
  // Dark rejim uchun inline override'lar
  const modalStyle = isDark ? { background: "#151D3F", color: "#E2E8F0", border: "1px solid rgba(255,255,255,.1)" } : {};
  const inputStyle = isDark ? { background: "#1F2A55", color: "#E2E8F0", borderColor: "rgba(255,255,255,.16)" } : {};
  const labelStyle = isDark ? { color: "#94A3B8" } : {};
  const [pwVisible, setPwVisible] = useState(false);
  const [confirmPwVisible, setConfirmPwVisible] = useState(false);
  const [currentPwVisible, setCurrentPwVisible] = useState(false);
  const eyeIcon = (visible: boolean) => visible ? (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 7 10 7a13.2 13.2 0 0 1-2.16 3.19M6.6 6.6A13.3 13.3 0 0 0 2 11s3.5 7 10 7a9 9 0 0 0 4.4-1.1" />
      <line x1="3" y1="3" x2="21" y2="21" />
    </svg>
  ) : (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" />
    </svg>
  );

  return (
    <div onClick={onClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal} style={modalStyle}>
        <div className={styles.head}>
          <div className={styles.headInfo}>
            <div className={styles.avatar}>{initial}</div>
            <div>
              <div className={styles.fullName} style={isDark ? { color: "#E2E8F0" } : {}}>{pFullName}</div>
              <div className={styles.handle}>{userHandle}</div>
            </div>
          </div>
          <HButton onClick={onClose} data-tip={s.close} aria-label={s.close} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "#E2E8F0", color: "#193070" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>

        <div className={styles.divider} />

        <div className={styles.fields}>
          {/* Ism va login endi TAHRIRLANADI — backendda PATCH /v1/users/me bor.
              Login band-emasligi backendda tekshiriladi: band bo'lsa 409
              qaytadi va xabar quyidagi xato maydonida chiqadi. */}
          <div>
            <label className={styles.fieldLabel} style={labelStyle} htmlFor="profile-fullname">{s.fullName}</label>
            <input id="profile-fullname" className={styles.input} style={inputStyle} value={pFullName} onChange={(e: ChangeEvent<HTMLInputElement>) => setPFullName(e.target.value)} placeholder={s.fullNamePh} autoComplete="name" />
          </div>
          <div>
            <label className={styles.fieldLabel} style={labelStyle} htmlFor="profile-username">{s.username}</label>
            <div className={styles.usernameField} style={inputStyle}>
              <span className={styles.usernamePrefix} aria-hidden="true">@</span>
              <input id="profile-username" className={styles.usernameInput} style={isDark ? { background: "transparent", color: "#E2E8F0" } : {}} value={pUsername} onChange={(e: ChangeEvent<HTMLInputElement>) => setPUsername(e.target.value)} placeholder={s.usernamePh} autoCapitalize="none" autoComplete="username" spellCheck={false} />
            </div>
          </div>
          {/* JORIY parol — yangi parol kiritilgandagina ko'rinadi.
              U bo'lmasa o'g'irlangan token bilan parolni almashtirib,
              hisob egasini butunlay bloklab qo'yish mumkin bo'lardi. */}
          {pPassword && (
            <div>
              <label className={styles.fieldLabel} style={labelStyle} htmlFor="profile-current-password">{s.currentPassword}</label>
              <div className={styles.pwField}>
                <input id="profile-current-password" className={styles.input} style={inputStyle} value={pCurrentPassword} onChange={(e: ChangeEvent<HTMLInputElement>) => setPCurrentPassword(e.target.value)} type={currentPwVisible ? "text" : "password"} placeholder={s.currentPasswordPh} autoComplete="current-password" />
                <button type="button" onClick={() => setCurrentPwVisible((v) => !v)} data-tip={currentPwVisible ? s.hidePassword : s.showPassword} aria-label={currentPwVisible ? s.hidePassword : s.showPassword} aria-pressed={currentPwVisible} className={styles.pwToggleBtn}>
                  {eyeIcon(currentPwVisible)}
                </button>
              </div>
              <div className={styles.fieldHint}>{s.currentPasswordHint}</div>
            </div>
          )}
          <div>
            <label className={styles.fieldLabel} style={labelStyle} htmlFor="profile-password">{s.newPassword}</label>
            <div className={styles.pwField}>
              <input id="profile-password" className={styles.input} style={inputStyle} value={pPassword} onChange={(e: ChangeEvent<HTMLInputElement>) => setPPassword(e.target.value)} type={pwVisible ? "text" : "password"} placeholder={s.newPasswordPh} autoComplete="new-password" />
              {/* tabIndex={-1} olib tashlandi — klaviatura bilan yetib bo'lmasdi */}
              <button type="button" onClick={() => setPwVisible((v) => !v)} data-tip={pwVisible ? s.hidePassword : s.showPassword} aria-label={pwVisible ? s.hidePassword : s.showPassword} aria-pressed={pwVisible} className={styles.pwToggleBtn}>
                {eyeIcon(pwVisible)}
              </button>
            </div>
          </div>
          {pPassword && (
            <div>
              <label className={styles.fieldLabel} style={labelStyle} htmlFor="profile-confirm-password">{s.confirmNewPassword}</label>
              <div className={styles.pwField}>
                <input id="profile-confirm-password" className={styles.input} style={inputStyle} value={pConfirmPassword} onChange={(e: ChangeEvent<HTMLInputElement>) => setPConfirmPassword(e.target.value)} type={confirmPwVisible ? "text" : "password"} placeholder={s.newPasswordPh} autoComplete="new-password" />
                <button type="button" onClick={() => setConfirmPwVisible((v) => !v)} data-tip={confirmPwVisible ? s.hidePassword : s.showPassword} aria-label={confirmPwVisible ? s.hidePassword : s.showPassword} aria-pressed={confirmPwVisible} className={styles.pwToggleBtn}>
                  {eyeIcon(confirmPwVisible)}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* role="alert" — ekran o'quvchisi xatoni O'ZI e'lon qiladi.
            Ilgari ko'zi ojiz foydalanuvchi "Saqlash" ni bosib, nega hech narsa
            bo'lmayotganini bilmasdi. */}
        {error && (
          <div className={styles.errorBox} role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="13" /><line x1="12" y1="16.5" x2="12" y2="16.5" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <HButton onClick={onSave} disabled={saving} aria-busy={saving} className={`${styles.saveBtn} ${saved ? styles.saveBtnSaved : styles.saveBtnIdle}`} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(25, 48, 112,.28)" }}>
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

        <HButton onClick={onLogout} className={styles.logoutBtn} baseStyle={{}} hoverStyle={{ background: "#FEF2F2", borderColor: "#FECACA" }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
          {s.logOut}
        </HButton>
      </div>
    </div>
  );
}
