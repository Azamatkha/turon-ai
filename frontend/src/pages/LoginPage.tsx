import { useState, CSSProperties, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";

// Turon AI logotipi (SVG)
const Logo = ({ size = 38 }: { size?: number }) => (
  <svg viewBox="0 0 300 304" width={size} height={size} style={{ display: "block" }}>
    <path
      d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z"
      fill="currentColor"
    />
  </svg>
);

// Bayroq (uz / ru)
const Flag = ({ code }: { code: "uz" | "ru" }) => {
  if (code === "ru") {
    return (
      <svg viewBox="0 0 9 6" width="100%" height="100%" style={{ display: "block" }}>
        <rect width={9} height={6} fill="#fff" />
        <rect y={2} width={9} height={2} fill="#0039A6" />
        <rect y={4} width={9} height={2} fill="#D52B1E" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 9 6" width="100%" height="100%" style={{ display: "block" }}>
      <rect width={9} height={6} fill="#fff" />
      <rect width={9} height={1.9} fill="#0099B5" />
      <rect y={4.1} width={9} height={1.9} fill="#1EB53A" />
      <circle cx={1.7} cy={1} r={0.55} fill="#fff" stroke="#CE1126" strokeWidth={0.18} />
      <circle cx={1.9} cy={1} r={0.5} fill="#0099B5" />
    </svg>
  );
};

// Ikki tildagi matnlar (i18n)
const STR = {
  uz: {
    badge: "Faqat ichki foydalanish",
    headline: "Bank jamoasi uchun aqlli yordamchi.",
    sub: "Mijozlar bilan muloqotni tayyorlash, mahsulot va siyosatlarni topish hamda ishni tezlashtirish uchun korporativ hisobingiz bilan kiring — xavfsiz.",
    sso: "Yagona tizimga kirish bilan himoyalangan · 256-bit shifrlash",
    signIn: "Kirish",
    welcome: "Xush kelibsiz. Davom etish uchun ma’lumotlaringizni kiriting.",
    invalid: "Login yoki parol noto‘g‘ri. Qayta urinib ko‘ring.",
    login: "Login",
    password: "Parol",
    loginPh: "masalan, a.karimov",
    remember: "Tizimda qoldir",
    help: "Yordam kerakmi?",
    monitored: "Sessiya xavfsizlik uchun kuzatiladi. Ruxsatsiz kirish taqiqlanadi.",
    label: "O‘zbekcha",
  },
  ru: {
    badge: "Только внутренний доступ",
    headline: "Умный помощник для команды банка.",
    sub: "Войдите с корпоративной учётной записью, чтобы готовить письма клиентам, находить продукты и работать быстрее — безопасно.",
    sso: "Защищено единым входом · 256-битное шифрование",
    signIn: "Войти",
    welcome: "Добро пожаловать. Введите данные для входа.",
    invalid: "Неверный логин или пароль. Попробуйте снова.",
    login: "Логин",
    password: "Пароль",
    loginPh: "напр., a.karimov",
    remember: "Запомнить меня",
    help: "Нужна помощь?",
    monitored: "Сессия отслеживается в целях безопасности. Несанкционированный доступ запрещён.",
    label: "Русский",
  },
} as const;

type Lang = keyof typeof STR;

export default function LoginPage() {
  const navigate = useNavigate();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [pwVisible, setPwVisible] = useState(false);
  const [remember, setRemember] = useState(false);
  const [focus, setFocus] = useState<"login" | "pw" | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [lang, setLang] = useState<Lang>("uz");
  const [langMenuOpen, setLangMenuOpen] = useState(false);

  const T = STR[lang];

  // Maydon (input) o'rovi uchun stil — fokuslanganda rangi o'zgaradi
  const field = (active: boolean): CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: "10px",
    background: "#fff",
    borderRadius: "12px",
    padding: "0 14px",
    height: "50px",
    border: "1.6px solid " + (active ? "#2f6690" : "#dde2dc"),
    boxShadow: active ? "0 0 0 4px rgba(47,102,144,.12)" : "0 1px 2px rgba(22,66,91,.03)",
    transition: "border-color .2s ease, box-shadow .2s ease",
  });

  const inputStyle: CSSProperties = {
    flex: 1,
    minWidth: 0,
    border: "none",
    outline: "none",
    background: "transparent",
    fontSize: "15px",
    color: "#16425b",
    height: "100%",
    padding: 0,
  };

  const submit = () => {
    if (loading) return;
    if (!login.trim() || !password.trim()) {
      setError(true);
      return;
    }
    setLoading(true);
    setError(false);
    // Hozircha backendga ulanmagan — 1.1s kutib chat sahifasiga o'tamiz
    setTimeout(() => navigate("/chat"), 1100);
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter") submit();
  };

  return (
    <div
      style={{
        height: "100vh",
        width: "100%",
        display: "flex",
        overflow: "hidden",
        background: "#d9dcd6",
        color: "#16425b",
      }}
    >
      {/* ===== BREND PANELI ===== */}
      <div
        style={{
          position: "relative",
          flex: 1.05,
          minWidth: 0,
          background: "linear-gradient(150deg,#16425b 0%,#2f6690 62%,#3a7ca5 100%)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "48px 52px",
          color: "#eef3f6",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "-120px",
            right: "-80px",
            width: "420px",
            height: "420px",
            borderRadius: "50%",
            background: "radial-gradient(circle at 30% 30%,rgba(217,220,214,.20),transparent 70%)",
            animation: "blobA 14s ease-in-out infinite",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-150px",
            left: "-110px",
            width: "500px",
            height: "500px",
            borderRadius: "50%",
            background: "radial-gradient(circle at 60% 40%,rgba(58,124,165,.45),transparent 70%)",
            animation: "blobB 18s ease-in-out infinite",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px)",
            backgroundSize: "46px 46px",
            WebkitMaskImage: "radial-gradient(circle at 72% 28%,#000,transparent 72%)",
            maskImage: "radial-gradient(circle at 72% 28%,#000,transparent 72%)",
            pointerEvents: "none",
          }}
        />

        {/* logo */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: "13px" }}>
          <div style={{ width: "38px", height: "38px", color: "#bfe0f0", animation: "floaty 6s ease-in-out infinite" }}>
            <Logo size={38} />
          </div>
          <div style={{ fontSize: "21px", fontWeight: 800, letterSpacing: "-.4px", whiteSpace: "nowrap" }}>
            Turon<span style={{ fontWeight: 400, opacity: 0.75 }}> AI</span>
          </div>
        </div>

        {/* sarlavha bloki */}
        <div style={{ position: "relative", maxWidth: "470px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 13px",
              border: "1px solid rgba(255,255,255,.22)",
              borderRadius: "99px",
              fontSize: "11.5px",
              fontWeight: 600,
              letterSpacing: ".5px",
              textTransform: "uppercase",
              color: "#cfe3ef",
              marginBottom: "22px",
              whiteSpace: "nowrap",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "99px",
                background: "#7fd1a8",
                boxShadow: "0 0 0 3px rgba(127,209,168,.25)",
              }}
            />
            {T.badge}
          </div>
          <h1
            style={{
              fontSize: "40px",
              lineHeight: 1.12,
              fontWeight: 700,
              letterSpacing: "-1px",
              margin: "0 0 16px",
              textWrap: "balance" as CSSProperties["textWrap"],
            }}
          >
            {T.headline}
          </h1>
          <p style={{ fontSize: "16px", lineHeight: 1.6, color: "rgba(238,243,246,.78)", margin: 0, maxWidth: "420px" }}>
            {T.sub}
          </p>
        </div>

        {/* pastki SSO qatori */}
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "12.5px",
            color: "rgba(238,243,246,.6)",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
          </svg>
          {T.sso}
        </div>
      </div>

      {/* ===== LOGIN PANELI ===== */}
      <div
        style={{
          position: "relative",
          flex: 1,
          minWidth: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "32px",
          background: "#f4f6f3",
        }}
      >
        {/* til tanlash dropdown */}
        <div style={{ position: "absolute", top: "24px", right: "26px", zIndex: 20 }}>
          <button
            onClick={() => setLangMenuOpen((v) => !v)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              background: "#fff",
              border: "1px solid #dde2dc",
              borderRadius: "11px",
              cursor: "pointer",
              boxShadow: "0 1px 3px rgba(22,66,91,.06)",
              transition: "all .16s ease",
            }}
          >
            <span style={{ width: "20px", height: "14px", borderRadius: "2px", overflow: "hidden", flex: "0 0 auto", boxShadow: "0 0 0 1px rgba(22,66,91,.12)", display: "block" }}>
              <Flag code={lang} />
            </span>
            <span style={{ fontSize: "13px", fontWeight: 600, color: "#16425b" }}>{lang === "ru" ? "RUS" : "UZB"}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7d909a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transition: "transform .22s ease", transform: langMenuOpen ? "rotate(180deg)" : "none" }}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {langMenuOpen && (
            <div
              style={{
                position: "absolute",
                top: "46px",
                right: 0,
                width: "178px",
                background: "#fff",
                border: "1px solid #e6eae3",
                borderRadius: "13px",
                padding: "5px",
                boxShadow: "0 16px 40px rgba(13,33,45,.18)",
                animation: "popIn .2s cubic-bezier(.2,.8,.3,1) both",
              }}
            >
              {(["uz", "ru"] as Lang[]).map((code) => (
                <button
                  key={code}
                  onClick={() => {
                    setLang(code);
                    setLangMenuOpen(false);
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    width: "100%",
                    padding: "9px 11px",
                    border: "none",
                    borderRadius: "9px",
                    background: lang === code ? "#eef3f6" : "transparent",
                    cursor: "pointer",
                    transition: "background .14s ease",
                  }}
                >
                  <span style={{ width: "22px", height: "15px", borderRadius: "2px", overflow: "hidden", flex: "0 0 auto", boxShadow: "0 0 0 1px rgba(22,66,91,.12)", display: "block" }}>
                    <Flag code={code} />
                  </span>
                  <span style={{ flex: 1, textAlign: "left", fontSize: "13.5px", fontWeight: 500, color: "#16425b" }}>{STR[code].label}</span>
                  {lang === code && (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2f6690" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* forma */}
        <div style={{ width: "100%", maxWidth: "386px" }}>
          <div style={{ marginBottom: "30px" }}>
            <h2 style={{ fontSize: "27px", fontWeight: 700, letterSpacing: "-.5px", margin: "0 0 7px", color: "#16425b" }}>{T.signIn}</h2>
            <p style={{ fontSize: "14.5px", color: "#6b7d86", margin: 0 }}>{T.welcome}</p>
          </div>

          {/* xato xabari */}
          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "9px",
                padding: "11px 14px",
                marginBottom: "18px",
                borderRadius: "11px",
                background: "#fdeceb",
                border: "1px solid #f6c9c5",
                color: "#c0392b",
                fontSize: "13.5px",
                fontWeight: 500,
                animation: "shake .4s ease both",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="8" x2="12" y2="13" />
                <line x1="12" y1="16.5" x2="12" y2="16.5" />
              </svg>
              <span>{T.invalid}</span>
            </div>
          )}

          {/* login maydoni */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px", letterSpacing: ".2px" }}>{T.login}</label>
            <div style={field(focus === "login")}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={focus === "login" ? "#2f6690" : "#9aafb8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto", transition: "stroke .2s ease" }}>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <input
                value={login}
                onChange={(e) => {
                  setLogin(e.target.value);
                  setError(false);
                }}
                onFocus={() => setFocus("login")}
                onBlur={() => setFocus(null)}
                onKeyDown={onKey}
                placeholder={T.loginPh}
                autoComplete="username"
                style={inputStyle}
              />
            </div>
          </div>

          {/* parol maydoni */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px", letterSpacing: ".2px" }}>{T.password}</label>
            <div style={field(focus === "pw")}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={focus === "pw" ? "#2f6690" : "#9aafb8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto", transition: "stroke .2s ease" }}>
                <rect x="4" y="11" width="16" height="10" rx="2.2" />
                <path d="M8 11V7a4 4 0 0 1 8 0v4" />
              </svg>
              <input
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(false);
                }}
                onFocus={() => setFocus("pw")}
                onBlur={() => setFocus(null)}
                onKeyDown={onKey}
                type={pwVisible ? "text" : "password"}
                placeholder="••••••••"
                autoComplete="current-password"
                style={inputStyle}
              />
              <button
                onClick={() => setPwVisible((v) => !v)}
                tabIndex={-1}
                title="Show / hide password"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flex: "0 0 auto",
                  width: "30px",
                  height: "30px",
                  border: "none",
                  borderRadius: "7px",
                  background: "transparent",
                  color: "#7d909a",
                  cursor: "pointer",
                  transition: "all .15s ease",
                }}
              >
                {pwVisible ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.5 0 10 7 10 7a13.2 13.2 0 0 1-2.16 3.19M6.6 6.6A13.3 13.3 0 0 0 2 11s3.5 7 10 7a9 9 0 0 0 4.4-1.1" />
                    <line x1="3" y1="3" x2="21" y2="21" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* eslab qolish + yordam */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
            <button onClick={() => setRemember((v) => !v)} style={{ display: "flex", alignItems: "center", gap: "8px", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "19px",
                  height: "19px",
                  borderRadius: "6px",
                  flex: "0 0 auto",
                  border: "1.8px solid " + (remember ? "#2f6690" : "#c2ccc9"),
                  background: remember ? "#2f6690" : "#fff",
                  transition: "all .18s ease",
                }}
              >
                {remember && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </span>
              <span style={{ fontSize: "13.5px", color: "#42565f", whiteSpace: "nowrap" }}>{T.remember}</span>
            </button>
            <a href="#" style={{ fontSize: "13.5px", fontWeight: 600, color: "#2f6690", textDecoration: "none", whiteSpace: "nowrap" }}>{T.help}</a>
          </div>

          {/* kirish tugmasi */}
          <button
            onClick={submit}
            style={{
              width: "100%",
              height: "52px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "none",
              borderRadius: "13px",
              cursor: loading ? "default" : "pointer",
              background: loading ? "#3a7ca5" : "linear-gradient(135deg,#2f6690,#16425b)",
              color: "#fff",
              fontSize: "15.5px",
              fontWeight: 600,
              letterSpacing: ".2px",
              boxShadow: "0 8px 22px rgba(22,66,91,.22)",
              transition: "transform .15s ease, box-shadow .2s ease, background .3s ease",
            }}
          >
            {loading ? (
              <span style={{ width: "18px", height: "18px", borderRadius: "50%", border: "2.4px solid rgba(255,255,255,.35)", borderTopColor: "#fff", animation: "spin .7s linear infinite" }} />
            ) : (
              <span style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                {T.signIn}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </span>
            )}
          </button>

          {/* pastki kuzatuv eslatmasi */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "26px", color: "#9aa7a2", fontSize: "12px" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="11" width="16" height="10" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
            {T.monitored}
          </div>
        </div>
      </div>
    </div>
  );
}
