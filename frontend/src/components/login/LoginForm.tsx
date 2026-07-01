import { KeyboardEvent, useState } from "react";
import { Link } from "react-router-dom";
import { GrLogin } from "react-icons/gr";
import { RiLockPasswordLine } from "react-icons/ri";
import LangSwitcher from "../LangSwitcher";
import type { Lang } from "../../types/lang";
import type { LoginStrings } from "../../types/i18n";
import styles from "./LoginForm.module.css";

interface LoginFormProps {
  t: LoginStrings;
  lang: Lang;
  setLang: (l: Lang) => void;
  login: string;
  setLogin: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  pwVisible: boolean;
  setPwVisible: (fn: (v: boolean) => boolean) => void;
  focus: "login" | "pw" | null;
  setFocus: (v: "login" | "pw" | null) => void;
  loading: boolean;
  error: boolean;
  submit: () => void;
  onKey: (e: KeyboardEvent) => void;
}

export default function LoginForm({
  t, lang, setLang,
  login, setLogin, password, setPassword, pwVisible, setPwVisible,
  focus, setFocus, loading, error, submit, onKey,
}: LoginFormProps) {
  const [helpOpen, setHelpOpen] = useState(false);
  return (
    <div className={styles.panel}>
      {/* til tanlash dropdown */}
      <div className={styles.langSwitcherWrap}>
        <LangSwitcher lang={lang} onChange={setLang} theme="light" align="right" />
      </div>

      {/* forma */}
      <div className={styles.formBox}>
        <div className={styles.headerBlock}>
          <h2 className={styles.title}>{t.signIn}</h2>
          <p className={styles.subtitle}>{t.welcome}</p>
        </div>

        {/* xato xabari */}
        {error && (
          <div className={styles.errorBox}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="9" />
              <line x1="12" y1="8" x2="12" y2="13" />
              <line x1="12" y1="16.5" x2="12" y2="16.5" />
            </svg>
            <span>{t.invalid}</span>
          </div>
        )}

        {/* login maydoni */}
        <div className={styles.fieldGroup}>
          <label className={styles.fieldLabel}>{t.login}</label>
          <div className={focus === "login" ? `${styles.field} ${styles.fieldActive}` : styles.field}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={focus === "login" ? "#2a6f97" : "#9aafb8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto", transition: "stroke .2s ease" }}>
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              className={styles.input}
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              onFocus={() => setFocus("login")}
              onBlur={() => setFocus(null)}
              onKeyDown={onKey}
              placeholder={t.loginPh}
              autoComplete="username"
            />
          </div>
        </div>

        {/* parol maydoni */}
        <div className={styles.fieldGroupTight}>
          <label className={styles.fieldLabel}>{t.password}</label>
          <div className={focus === "pw" ? `${styles.field} ${styles.fieldActive}` : styles.field}>
            <RiLockPasswordLine size={19} color={focus === "pw" ? "#2a6f97" : "#9aafb8"} style={{ flex: "0 0 auto", transition: "color .2s ease" }} />
            <input
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFocus("pw")}
              onBlur={() => setFocus(null)}
              onKeyDown={onKey}
              type={pwVisible ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
            />
            <button onClick={() => setPwVisible((v) => !v)} tabIndex={-1} title="Show / hide password" className={styles.pwToggleBtn}>
              {pwVisible ? (
                // parol KO'RINIB turibdi -> "yopiq ko'z" (bosilsa yashiradi)
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 7 10 7a13.2 13.2 0 0 1-2.16 3.19M6.6 6.6A13.3 13.3 0 0 0 2 11s3.5 7 10 7a9 9 0 0 0 4.4-1.1" />
                  <line x1="3" y1="3" x2="21" y2="21" />
                </svg>
              ) : (
                // parol YASHIRIN -> "ochiq ko'z" (bosilsa ko'rsatadi)
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* yordam */}
        <div className={styles.rememberRow} style={{ justifyContent: "flex-end" }}>
          <div className={styles.helpWrap}>
            <button type="button" onClick={() => setHelpOpen((v) => !v)} className={styles.helpLink} tabIndex={-1}>
              {t.help}
            </button>
            {helpOpen && (
              <div className={styles.helpPop} role="status">
                {lang === "ru" ? "Служба поддержки" : lang === "uz_cyrl" ? "Ёрдам маркази" : "Yordam markazi"}
                {": "}
                <span className={styles.helpPhone}>1234</span>
              </div>
            )}
          </div>
        </div>

        {/* kirish tugmasi */}
        <button onClick={submit} className={loading ? `${styles.submitBtn} ${styles.submitBtnLoading}` : styles.submitBtn}>
          {loading ? (
            <span className={styles.spinner} />
          ) : (
            <span className={`${styles.submitContent} ${styles.submitText}`}>
              {t.signIn}
              <GrLogin size={17} color="#fff" />
            </span>
          )}
        </button>

        {/* ro'yxatdan o'tish havolasi */}
        <div className={styles.monitoredRow} style={{ justifyContent: "center", gap: 6 }}>
          {lang === "ru" ? "Нет аккаунта?" : lang === "uz_cyrl" ? "Ҳисобингиз йўқми?" : "Hisobingiz yo‘qmi?"}
          <Link to="/register" style={{ color: "#2a6f97", fontWeight: 600 }}>
            {lang === "ru" ? "Регистрация" : lang === "uz_cyrl" ? "Рўйхатдан ўтиш" : "Ro‘yxatdan o‘tish"}
          </Link>
        </div>
      </div>
    </div>
  );
}
