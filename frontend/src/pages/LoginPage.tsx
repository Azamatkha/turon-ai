import { useState, CSSProperties, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import DotGrid from "../components/DotGrid";
import LangSwitcher from "../components/LangSwitcher";

// Turon AI logotipi (SVG)
const Logo = ({ size = 38 }: { size?: number }) => (
  <svg viewBox="0 0 300 304" width={size} height={size} style={{ display: "block" }}>
    <path
      d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z"
      fill="currentColor"
    />
  </svg>
);

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
    online: "Onlayn",
    pvUser: "Omonat depozit shartlarini tushuntirib bera olasizmi?",
    pvAI: "Albatta. Joriy stavka yiliga 18% — qisqacha bayon qilib beraymi?",
    statLabel: "Hal qilingan so‘rovlar",
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
    online: "Онлайн",
    pvUser: "Можешь объяснить условия срочного депозита?",
    pvAI: "Конечно. Текущая ставка — 18% годовых. Сделать краткую сводку?",
    statLabel: "Решённые запросы",
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
        position: "relative",
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "28px",
        overflow: "hidden",
        background: "radial-gradient(circle at 50% 0%,#e6edef 0%,#d4dee2 55%,#bfd0d8 100%)",
        color: "#16425b",
        boxSizing: "border-box",
      }}
    >
      {/* ===== SAHIFA FONI: aurora dog'lari + interaktiv nuqta-to'r (login qutisidan tashqarida) ===== */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            top: "-12%",
            left: "-8%",
            width: "46vw",
            height: "46vw",
            borderRadius: "50%",
            background: "radial-gradient(circle at 35% 35%,rgba(47,102,144,.22),transparent 68%)",
            filter: "blur(20px)",
            animation: "blobA 16s ease-in-out infinite",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-16%",
            right: "-10%",
            width: "52vw",
            height: "52vw",
            borderRadius: "50%",
            background: "radial-gradient(circle at 60% 40%,rgba(58,124,165,.20),transparent 70%)",
            filter: "blur(20px)",
            animation: "blobB 20s ease-in-out infinite",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "55%",
            width: "30vw",
            height: "30vw",
            borderRadius: "50%",
            background: "radial-gradient(circle at 50% 50%,rgba(127,179,210,.16),transparent 72%)",
            filter: "blur(24px)",
            animation: "blobA 24s ease-in-out infinite reverse",
          }}
        />
      </div>
      <div style={{ position: "absolute", inset: 0, zIndex: 0, pointerEvents: "none" }}>
        <DotGrid
          dotSize={4}
          gap={28}
          baseColor="#c2cdd2"
          activeColor="#2f6690"
          proximity={130}
          shockRadius={240}
          shockStrength={4}
          resistance={750}
          returnDuration={1.5}
        />
      </div>

      <div
        style={{
          position: "relative",
          zIndex: 1,
          width: "100%",
          maxWidth: "1140px",
          height: "min(660px, calc(100vh - 56px))",
          display: "flex",
          borderRadius: "26px",
          overflow: "hidden",
          background: "#fff",
          boxShadow: "0 40px 80px -20px rgba(13,33,45,.32), 0 0 0 1px rgba(22,66,91,.04)",
        }}
      >
      {/* ===== BREND PANELI ===== */}
      <div
        style={{
          position: "relative",
          flex: 1.05,
          minWidth: 0,
          background: "linear-gradient(150deg,#0f3145 0%,#16425b 38%,#2f6690 78%,#3a7ca5 100%)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "32px 36px",
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
            background: "radial-gradient(circle at 30% 30%,rgba(217,220,214,.18),transparent 70%)",
            animation: "blobA 14s ease-in-out infinite",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-150px",
            left: "-110px",
            width: "520px",
            height: "520px",
            borderRadius: "50%",
            background: "radial-gradient(circle at 60% 40%,rgba(58,124,165,.42),transparent 70%)",
            animation: "blobB 18s ease-in-out infinite",
            pointerEvents: "none",
          }}
        />
        {/* interaktiv nuqta-to'r foni (sichqoncha yaqinida yorishadi, bosilganda to'lqin) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 1,
            opacity: 0.9,
            WebkitMaskImage: "radial-gradient(circle at 64% 42%,#000,transparent 82%)",
            maskImage: "radial-gradient(circle at 64% 42%,#000,transparent 82%)",
            pointerEvents: "none",
          }}
        >
          <DotGrid
            dotSize={4}
            gap={22}
            baseColor="#2c5570"
            activeColor="#bfe0f0"
            proximity={120}
            shockRadius={220}
            shockStrength={4}
            resistance={750}
            returnDuration={1.5}
          />
        </div>
        {/* sochilgan bezak kvadratchalar */}
        <div style={{ position: "absolute", top: "34px", left: "38px", width: "30px", height: "30px", borderRadius: "7px", background: "rgba(255,255,255,.05)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "120px", left: "64px", width: "18px", height: "18px", borderRadius: "5px", background: "rgba(255,255,255,.06)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "80px", left: "120px", width: "26px", height: "26px", borderRadius: "6px", background: "rgba(127,209,168,.12)", pointerEvents: "none" }} />

        {/* logo */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: "11px", zIndex: 2 }}>
          <div style={{ width: "32px", height: "32px", color: "#bfe0f0" }}>
            <Logo size={32} />
          </div>
          <div style={{ fontSize: "18px", fontWeight: 800, letterSpacing: "-.4px", whiteSpace: "nowrap" }}>
            Turon<span style={{ fontWeight: 400, opacity: 0.75 }}> AI</span>
          </div>
        </div>

        {/* suzuvchi mahsulot oldindan ko'rinishi */}
        <div style={{ position: "relative", zIndex: 2, flex: 1, display: "flex", alignItems: "flex-start", justifyContent: "center", minHeight: 0, padding: "4px 0 0" }}>
          <div style={{ position: "relative", width: "258px", maxWidth: "100%" }}>
            {/* asosiy chat karta */}
            <div
              style={{
                position: "relative",
                background: "rgba(255,255,255,.96)",
                borderRadius: "18px",
                padding: "14px",
                boxShadow: "0 26px 50px -16px rgba(8,25,36,.6), 0 0 0 1px rgba(255,255,255,.4) inset",
                animation: "floatA 8s ease-in-out infinite",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "9px", paddingBottom: "10px", borderBottom: "1px solid #eef1ec", marginBottom: "11px" }}>
                <div style={{ width: "26px", height: "26px", borderRadius: "8px", background: "linear-gradient(140deg,#16425b,#2f6690)", display: "flex", alignItems: "center", justifyContent: "center", flex: "0 0 auto" }}>
                  <svg viewBox="0 0 300 304" width="14" height="14"><path d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z" fill="#dbe7f0" /></svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#16425b", lineHeight: 1.1 }}>Turon AI</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "10px", color: "#6b7d86", marginTop: "2px" }}>
                    <span style={{ width: "5px", height: "5px", borderRadius: "99px", background: "#34c77b" }} />
                    {T.online}
                  </div>
                </div>
                <div style={{ fontSize: "9.5px", fontWeight: 600, color: "#9aafb8", letterSpacing: ".4px" }}>v2.5</div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "8px" }}>
                <div style={{ maxWidth: "80%", background: "#2f6690", color: "#fff", fontSize: "11.5px", lineHeight: 1.4, padding: "7px 11px", borderRadius: "13px 13px 4px 13px" }}>{T.pvUser}</div>
              </div>
              <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
                <div style={{ maxWidth: "84%", background: "#f3f6f1", color: "#1c3c4d", fontSize: "11.5px", lineHeight: 1.45, padding: "7px 11px", borderRadius: "4px 13px 13px 13px" }}>{T.pvAI}</div>
              </div>
            </div>

            {/* suzuvchi statistika karta */}
            <div
              style={{
                position: "absolute",
                right: "-22px",
                bottom: "-16px",
                width: "148px",
                background: "rgba(255,255,255,.97)",
                borderRadius: "15px",
                padding: "12px",
                boxShadow: "0 22px 44px -14px rgba(8,25,36,.55), 0 0 0 1px rgba(255,255,255,.4) inset",
                animation: "floatB 7s ease-in-out infinite",
              }}
            >
              <div style={{ fontSize: "10.5px", fontWeight: 600, color: "#6b7d86", marginBottom: "9px" }}>{T.statLabel}</div>
              <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
                <div style={{ position: "relative", width: "50px", height: "50px", flex: "0 0 auto", borderRadius: "50%", background: "conic-gradient(#2f6690 0% 94%,#e3e8e2 94% 100%)" }}>
                  <div style={{ position: "absolute", inset: "7px", borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12.5px", fontWeight: 800, color: "#16425b" }}>94%</div>
                </div>
                <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "42px" }}>
                  <div style={{ width: "6px", height: "60%", borderRadius: "2px", background: "#cddbe5" }} />
                  <div style={{ width: "6px", height: "85%", borderRadius: "2px", background: "#3a7ca5" }} />
                  <div style={{ width: "6px", height: "45%", borderRadius: "2px", background: "#cddbe5" }} />
                  <div style={{ width: "6px", height: "100%", borderRadius: "2px", background: "#2f6690" }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* sarlavha bloki */}
        <div style={{ position: "relative", zIndex: 2 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 13px",
              border: "1px solid rgba(255,255,255,.22)",
              borderRadius: "99px",
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: ".5px",
              textTransform: "uppercase",
              color: "#cfe3ef",
              marginBottom: "12px",
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
              fontSize: "22px",
              lineHeight: 1.18,
              fontWeight: 700,
              letterSpacing: "-.4px",
              margin: "0 0 8px",
              maxWidth: "340px",
              textWrap: "balance" as CSSProperties["textWrap"],
            }}
          >
            {T.headline}
          </h1>
          <p style={{ fontSize: "12.5px", lineHeight: 1.55, color: "rgba(238,243,246,.78)", margin: "0 0 13px", maxWidth: "340px" }}>
            {T.sub}
          </p>
          {/* pastki SSO qatori */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "10.5px",
              color: "rgba(238,243,246,.55)",
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
            </svg>
            {T.sso}
          </div>
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
          padding: "32px 36px",
          background: "#f4f6f3",
        }}
      >
        {/* til tanlash dropdown */}
        <div style={{ position: "absolute", top: "24px", right: "26px", zIndex: 20 }}>
          <LangSwitcher lang={lang} onChange={setLang} theme="light" align="right" />
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
    </div>
  );
}
