import { KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import LangSwitcher from "../LangSwitcher";
import type { Lang } from "../../types/lang";
import styles from "./LoginForm.module.css";

// Register sahifasi uchun qisqa matnlar (login dizayni qayta ishlatiladi)
const STR: Record<Lang, {
  title: string; sub: string; fullName: string; fullNamePh: string;
  username: string; usernamePh: string; dept: string; deptPh: string;
  password: string; submit: string; have: string; signin: string;
}> = {
  uz: {
    title: "Ro‘yxatdan o‘tish", sub: "Yangi hisob yarating.",
    fullName: "To‘liq ism", fullNamePh: "masalan, Aziz Karimov",
    username: "Login", usernamePh: "masalan, a.karimov",
    dept: "Bo‘lim", deptPh: "masalan, Chakana", password: "Parol",
    submit: "Ro‘yxatdan o‘tish", have: "Hisobingiz bormi?", signin: "Kirish",
  },
  uz_cyrl: {
    title: "Рўйхатдан ўтиш", sub: "Янги ҳисоб яратинг.",
    fullName: "Тўлиқ исм", fullNamePh: "масалан, Азиз Каримов",
    username: "Логин", usernamePh: "масалан, a.karimov",
    dept: "Бўлим", deptPh: "масалан, Чакана", password: "Парол",
    submit: "Рўйхатдан ўтиш", have: "Ҳисобингиз борми?", signin: "Кириш",
  },
  ru: {
    title: "Регистрация", sub: "Создайте новый аккаунт.",
    fullName: "Полное имя", fullNamePh: "например, Азиз Каримов",
    username: "Логин", usernamePh: "например, a.karimov",
    dept: "Отдел", deptPh: "например, Розница", password: "Пароль",
    submit: "Зарегистрироваться", have: "Уже есть аккаунт?", signin: "Войти",
  },
};

interface Props {
  lang: Lang;
  setLang: (l: Lang) => void;
  fullName: string; setFullName: (v: string) => void;
  username: string; setUsername: (v: string) => void;
  department: string; setDepartment: (v: string) => void;
  password: string; setPassword: (v: string) => void;
  pwVisible: boolean; setPwVisible: (fn: (v: boolean) => boolean) => void;
  loading: boolean;
  error: string;
  submit: () => void;
  onKey: (e: KeyboardEvent) => void;
}

export default function RegisterForm(p: Props) {
  const t = STR[p.lang];
  return (
    <div className={styles.panel}>
      <div className={styles.langSwitcherWrap}>
        <LangSwitcher lang={p.lang} onChange={p.setLang} theme="light" align="right" />
      </div>

      <div className={styles.formBox}>
        <div className={styles.headerBlock}>
          <h2 className={styles.title}>{t.title}</h2>
          <p className={styles.subtitle}>{t.sub}</p>
        </div>

        {p.error && (
          <div className={styles.errorBox}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="13" /><line x1="12" y1="16.5" x2="12" y2="16.5" />
            </svg>
            <span>{p.error}</span>
          </div>
        )}

        <div className={styles.fieldGroup}>
          <label className={styles.fieldLabel}>{t.fullName}</label>
          <div className={styles.field}>
            <input className={styles.input} value={p.fullName} onChange={(e) => p.setFullName(e.target.value)} onKeyDown={p.onKey} placeholder={t.fullNamePh} />
          </div>
        </div>

        <div className={styles.fieldGroupTight}>
          <label className={styles.fieldLabel}>{t.username}</label>
          <div className={styles.field}>
            <input className={styles.input} value={p.username} onChange={(e) => p.setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ""))} onKeyDown={p.onKey} placeholder={t.usernamePh} autoCapitalize="none" autoComplete="username" />
          </div>
        </div>

        <div className={styles.fieldGroupTight}>
          <label className={styles.fieldLabel}>{t.dept}</label>
          <div className={styles.field}>
            <input className={styles.input} value={p.department} onChange={(e) => p.setDepartment(e.target.value)} onKeyDown={p.onKey} placeholder={t.deptPh} />
          </div>
        </div>

        <div className={styles.fieldGroupTight}>
          <label className={styles.fieldLabel}>{t.password}</label>
          <div className={styles.field}>
            <input className={styles.input} value={p.password} onChange={(e) => p.setPassword(e.target.value)} onKeyDown={p.onKey} type={p.pwVisible ? "text" : "password"} placeholder="••••••••" autoComplete="new-password" />
            <button onClick={() => p.setPwVisible((v) => !v)} tabIndex={-1} title="Show / hide password" className={styles.pwToggleBtn}>
              {p.pwVisible ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 7 10 7a13.2 13.2 0 0 1-2.16 3.19M6.6 6.6A13.3 13.3 0 0 0 2 11s3.5 7 10 7a9 9 0 0 0 4.4-1.1" />
                  <line x1="3" y1="3" x2="21" y2="21" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
        </div>

        <button onClick={p.submit} className={p.loading ? `${styles.submitBtn} ${styles.submitBtnLoading}` : styles.submitBtn} style={{ marginTop: 18 }}>
          {p.loading ? <span className={styles.spinner} /> : (
            <span className={`${styles.submitContent} ${styles.submitText}`}>
              {t.submit}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
            </span>
          )}
        </button>

        <div className={styles.monitoredRow} style={{ justifyContent: "center", gap: 6 }}>
          {t.have} <Link to="/login" style={{ color: "#2a6f97", fontWeight: 600 }}>{t.signin}</Link>
        </div>
      </div>
    </div>
  );
}
