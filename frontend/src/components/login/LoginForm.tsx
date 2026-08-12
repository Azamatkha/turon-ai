import { KeyboardEvent, useEffect, useState } from "react";
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
  error: "" | "invalid" | "rateLimited";
  submit: () => void;
  onKey: (e: KeyboardEvent) => void;
}

export default function LoginForm({
  t, lang, setLang,
  login, setLogin, password, setPassword, pwVisible, setPwVisible,
  focus, setFocus, loading, error, submit, onKey,
}: LoginFormProps) {
  const [helpOpen, setHelpOpen] = useState(false);
  const [hintOpen, setHintOpen] = useState(false);

  // Modal Esc bilan ham yopilsin (klaviatura bilan ishlaydiganlar uchun).
  useEffect(() => {
    if (!hintOpen) return;
    const onEsc = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setHintOpen(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [hintOpen]);
  return (
    <div className={styles.panel}>
      {/* til tanlash dropdown */}
      <div className={styles.langSwitcherWrap}>
        <LangSwitcher lang={lang} onChange={setLang} theme="light" align="right" tip={t.selectLanguage} />
      </div>

      {/* Forma.
          <form> ELEMENTI SHART (ilgari oddiy <div> edi):
          - parol menejerlari (bank kompyuterlarida korporativ menejer bo'lishi
            mumkin) faqat haqiqiy formani tanib, avtomatik to'ldiradi;
          - ekran o'quvchisi "forma" deb e'lon qiladi;
          - Enter tugmasi o'z-o'zidan ishlaydi — har bir maydonga alohida
            onKeyDown ulash kerak emas. */}
      <form
        className={styles.formBox}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        noValidate
      >
        <div className={styles.headerBlock}>
          {/* <h2>, <h1> emas: sahifaning asosiy sarlavhasi (h1) brend
              panelidagi shior. Bitta sahifada ikkita h1 bo'lsa, ekran
              o'quvchisining sarlavhalar bo'yicha navigatsiyasi buziladi. */}
          <h2 className={styles.title}>{t.signIn}</h2>
          <p className={styles.subtitle}>{t.welcome}</p>
        </div>

        {/* Xato xabari.
            role="alert" — ekran o'quvchisi xatoni DARHOL o'qiydi. Ilgari bu
            yo'q edi: ko'zi ojiz foydalanuvchi "Kirish" ni bosardi, hech narsa
            eshitmasdi va nega kira olmayotganini bilmasdi. */}
        <div aria-live="assertive" aria-atomic="true">
          {error && (
            <div className={styles.errorBox} role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="8" x2="12" y2="13" />
                <line x1="12" y1="16.5" x2="12" y2="16.5" />
              </svg>
              <span>{error === "rateLimited" ? t.rateLimited : t.invalid}</span>
            </div>
          )}
        </div>

        {/* login maydoni — label htmlFor/id juftligi bilan bog'langan:
            yorliqni bosganda maydon fokuslanadi, ekran o'quvchisi maydon
            nomini o'qiydi ("nomsiz matn maydoni" emas). */}
        <div className={styles.fieldGroup}>
          <label className={styles.fieldLabel} htmlFor="login-username">{t.login}</label>
          <div className={focus === "login" ? `${styles.field} ${styles.fieldActive}` : styles.field}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={focus === "login" ? "var(--tu-accent)" : "var(--tu-text-faint)"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto", transition: "stroke .2s ease" }} aria-hidden="true">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              id="login-username"
              name="username"
              className={styles.input}
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              onFocus={() => setFocus("login")}
              onBlur={() => setFocus(null)}
              onKeyDown={onKey}
              placeholder={t.loginPh}
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              required
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : undefined}
            />
          </div>
        </div>

        {/* parol maydoni */}
        <div className={styles.fieldGroupTight}>
          <label className={styles.fieldLabel} htmlFor="login-password">{t.password}</label>
          <div className={focus === "pw" ? `${styles.field} ${styles.fieldActive}` : styles.field}>
            <RiLockPasswordLine size={19} color={focus === "pw" ? "var(--tu-accent)" : "var(--tu-text-faint)"} style={{ flex: "0 0 auto", transition: "color .2s ease" }} aria-hidden="true" />
            <input
              id="login-password"
              name="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFocus("pw")}
              onBlur={() => setFocus(null)}
              onKeyDown={onKey}
              type={pwVisible ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : undefined}
            />
            {/* tabIndex={-1} OLIB TASHLANDI: u tugmani klaviatura
                navigatsiyasidan butunlay chiqarib tashlagan edi, ya'ni faqat
                klaviatura bilan ishlaydigan foydalanuvchi parolini ko'ra
                olmasdi (WCAG 2.1.1 buzilishi).
                type="button" — aks holda <form> ichida u submit qilib yuboradi. */}
            <button type="button" onClick={() => setPwVisible((v) => !v)} data-tip={pwVisible ? t.hidePassword : t.showPassword} aria-label={pwVisible ? t.hidePassword : t.showPassword} aria-pressed={pwVisible} className={styles.pwToggleBtn}>
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

        {/* yordam — tabIndex={-1} olib tashlandi (klaviatura bilan yetib
            bo'lmasdi), aria-expanded qo'shildi */}
        <div className={styles.rememberRow} style={{ justifyContent: "flex-end" }}>
          <div className={styles.helpWrap}>
            <button
              type="button"
              onClick={() => setHelpOpen((v) => !v)}
              className={styles.helpLink}
              aria-expanded={helpOpen}
            >
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

        {/* Kirish tugmasi.
            type="submit" — Enter bilan ham, bosish bilan ham bir xil yo'l.
            disabled + aria-busy — yuklanayotganda ikki marta yuborilmaydi va
            ekran o'quvchisi "band" ekanini aytadi. */}
        <button
          type="submit"
          disabled={loading}
          aria-busy={loading}
          className={loading ? `${styles.submitBtn} ${styles.submitBtnLoading}` : styles.submitBtn}
        >
          {loading ? (
            <>
              <span className={styles.spinner} aria-hidden="true" />
              <span className="sr-only">{t.signIn}…</span>
            </>
          ) : (
            <span className={`${styles.submitContent} ${styles.submitText}`}>
              {t.signIn}
              <GrLogin size={17} color="#fff" aria-hidden="true" />
            </span>
          )}
        </button>

        {/* Ro'yxatdan o'tish saytda YOPILGAN — havola o'rniga izoh chiqadi.
            HOVER YO'Q, faqat bosish: sichqoncha "Kirish" tugmasiga borayotib
            ustidan o'tsa quti ochilib, formani surib yuborardi. */}
        <div className={styles.monitoredRow} style={{ justifyContent: "center" }}>
          <button
            type="button"
            className={styles.noAccountBtn}
            onClick={() => setHintOpen(true)}
          >
            {t.noAccount}
          </button>
        </div>
      </form>

      {/* Modal — ekran markazida, oqimdan tashqarida. Shuning uchun ochilganda
          forma joyidan siljimaydi va panel chegarasi uni kesmaydi.

          role="dialog" endi ICHKI panelda (ilgari overlay'da edi — ekran
          o'quvchisi butun qorayish qatlamini "dialog" deb o'qirdi).
          aria-labelledby modal nomini dialogga bog'laydi. */}
      {hintOpen && (
        <div className={styles.hintOverlay} onClick={() => setHintOpen(false)}>
          <div
            className={styles.hintModal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="hint-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.hintTitle} id="hint-title">{t.noAccount}</div>
            <p className={styles.hintText}>{t.registerMobileOnly}</p>
            <button
              type="button"
              className={styles.hintClose}
              onClick={() => setHintOpen(false)}
              autoFocus
            >
              {t.gotIt}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
