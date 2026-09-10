import { ChangeEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { useTheme } from "../contexts/ThemeContext";
import { chatDict, chatStaticDict } from "../locales";
import { fetchMe, logout, changePassword, updateProfile, type Me } from "../services/authService";
import styles from "./ProfilePage.module.css";

// "2001-05-14" -> "14.05.2001"
function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}.${m}.${y}` : iso;
}

function EyeIcon({ visible }: { visible: boolean }) {
  return visible ? (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 7 10 7a13.2 13.2 0 0 1-2.16 3.19M6.6 6.6A13.3 13.3 0 0 0 2 11s3.5 7 10 7a9 9 0 0 0 4.4-1.1" />
      <line x1="3" y1="3" x2="21" y2="21" />
    </svg>
  ) : (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" />
    </svg>
  );
}

// Profil — alohida sahifa (/profile). Avval chat ustida modal edi va chat
// foni bilan qo'shilib, o'qib bo'lmay qolardi.
export default function ProfilePage() {
  const navigate = useNavigate();
  const { lang } = useLang(chatDict);
  const S = chatStaticDict[lang];
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const [me, setMe] = useState<Me | null>(null);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwVisible, setPwVisible] = useState(false);
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((m) => {
        setMe(m);
        setFullName(m.full_name);
        setUsername(m.username);
      })
      .catch(() => navigate("/login"));
  }, [navigate]);

  // Ism/login (PATCH /v1/users/me) va parol (PATCH /v1/users/me/password).
  // Tartib muhim: avval ism/login, keyin parol — parol o'zgarganda backend
  // BARCHA sessiyalarni bekor qiladi va keyingi so'rov 401 bo'lardi.
  const save = async () => {
    if (!me || saving) return;
    setError("");
    const nameChanged = fullName.trim() !== me.full_name;
    const usernameChanged = username.trim().toLowerCase() !== me.username;
    const wantsPasswordChange = !!password;
    if (!nameChanged && !usernameChanged && !wantsPasswordChange) return;

    // O'zi to'g'ri terganini tekshirish uchun tasdiqlash bilan solishtiramiz
    if (wantsPasswordChange && password !== confirm) {
      setError(S.passwordMismatch);
      return;
    }

    setSaving(true);
    try {
      if (nameChanged || usernameChanged) {
        const updated = await updateProfile({
          ...(nameChanged ? { full_name: fullName.trim() } : {}),
          ...(usernameChanged ? { username: username.trim().toLowerCase() } : {}),
        });
        // Backend normalizatsiya qilgan qiymatlar (kichik harf, ortiqcha bo'shliqsiz)
        setMe(updated);
        setFullName(updated.full_name);
        setUsername(updated.username);
      }

      if (wantsPasswordChange) {
        await changePassword(password);
        // Parol o'zgardi -> barcha sessiyalar yopildi -> yangi parol bilan qayta kirish
        await logout();
        navigate("/login");
        return;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Saqlashda xatolik");
      return;
    } finally {
      setSaving(false);
    }

    setPassword("");
    setConfirm("");
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  const displayName = me?.full_name || me?.username || "";
  const initial = (displayName || "?").charAt(0).toUpperCase();
  const documentText = [me?.doc_seria, me?.doc_number].filter(Boolean).join(" ");
  const infoRows: [string, string][] = [
    [S.infoPatronym, me?.patronym ?? ""],
    [S.infoPosition, me?.position ?? ""],
    [S.infoDepartment, me?.department ?? ""],
    [S.infoBranch, me?.branch ?? ""],
    [S.infoPnfl, me?.pnfl ?? ""],
    [S.infoBirthDate, formatDate(me?.birth_date)],
    [S.infoDocument, documentText],
  ];

  return (
    <div className={`${styles.page} ${isDark ? styles.dark : ""}`}>
      <div className={styles.container}>
        <div className={styles.topBar}>
          <button type="button" className={styles.backBtn} onClick={() => navigate("/")}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></svg>
            {S.backToChat}
          </button>
          <h1 className={styles.pageTitle}>{S.profileTitle}</h1>
        </div>

        <section className={`${styles.card} ${styles.hero}`}>
          <div className={styles.avatar}>{initial}</div>
          <div className={styles.heroText}>
            <div className={styles.heroName}>{displayName}</div>
            <div className={styles.heroMeta}>
              @{me?.username}
              {me?.position ? ` · ${me.position}` : ""}
            </div>
          </div>
        </section>

        <div className={styles.grid}>
          {/* Chap: tahrirlanadigan maydonlar */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{S.accountSettings}</h2>
            <div className={styles.fields}>
              <div>
                <label className={styles.fieldLabel} htmlFor="profile-fullname">{S.fullName}</label>
                <input id="profile-fullname" className={styles.input} value={fullName} onChange={(e: ChangeEvent<HTMLInputElement>) => setFullName(e.target.value)} placeholder={S.fullNamePh} autoComplete="name" />
              </div>
              <div>
                <label className={styles.fieldLabel} htmlFor="profile-username">{S.username}</label>
                <div className={styles.usernameField}>
                  <span className={styles.usernamePrefix} aria-hidden="true">@</span>
                  <input id="profile-username" className={styles.usernameInput} value={username} onChange={(e: ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)} placeholder={S.usernamePh} autoCapitalize="none" autoComplete="username" spellCheck={false} />
                </div>
              </div>
              <div>
                <label className={styles.fieldLabel} htmlFor="profile-password">{S.newPassword}</label>
                <div className={styles.pwField}>
                  <input id="profile-password" className={styles.input} value={password} onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)} type={pwVisible ? "text" : "password"} placeholder={S.newPasswordPh} autoComplete="new-password" />
                  <button type="button" onClick={() => setPwVisible((v) => !v)} aria-label={pwVisible ? S.hidePassword : S.showPassword} aria-pressed={pwVisible} className={styles.pwToggleBtn}>
                    <EyeIcon visible={pwVisible} />
                  </button>
                </div>
              </div>
              {password && (
                <div>
                  <label className={styles.fieldLabel} htmlFor="profile-confirm-password">{S.confirmNewPassword}</label>
                  <div className={styles.pwField}>
                    <input id="profile-confirm-password" className={styles.input} value={confirm} onChange={(e: ChangeEvent<HTMLInputElement>) => setConfirm(e.target.value)} type={confirmVisible ? "text" : "password"} placeholder={S.newPasswordPh} autoComplete="new-password" />
                    <button type="button" onClick={() => setConfirmVisible((v) => !v)} aria-label={confirmVisible ? S.hidePassword : S.showPassword} aria-pressed={confirmVisible} className={styles.pwToggleBtn}>
                      <EyeIcon visible={confirmVisible} />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className={styles.errorBox} role="alert">{error}</div>
            )}

            <button type="button" onClick={save} disabled={saving || !me} aria-busy={saving} className={`${styles.saveBtn} ${saved ? styles.saveBtnSaved : ""}`}>
              {saved && (
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12" /></svg>
              )}
              {saved ? S.saved : S.saveChanges}
            </button>
          </section>

          {/* O'ng: mobil verifikatsiyadan kelgan ma'lumotlar (faqat o'qish) */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{S.employeeInfo}</h2>
            <dl className={styles.infoList}>
              {infoRows.map(([label, value]) => (
                <div key={label} className={styles.infoRow}>
                  <dt className={styles.infoLabel}>{label}</dt>
                  <dd className={styles.infoValue}>{value || "—"}</dd>
                </div>
              ))}
            </dl>
            <div className={styles.hint}>{S.employeeInfoHint}</div>
          </section>
        </div>

        <section className={`${styles.card} ${styles.bottomRow}`}>
          <div className={styles.support}>
            <svg className={styles.supportIcon} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" /></svg>
            <span className={styles.supportHint}>{S.supportHint}</span>
            <span className={styles.supportNumber}>{S.supportNumber}</span>
          </div>
          <button type="button" onClick={doLogout} className={styles.logoutBtn}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
            {S.logOut}
          </button>
        </section>
      </div>
    </div>
  );
}
