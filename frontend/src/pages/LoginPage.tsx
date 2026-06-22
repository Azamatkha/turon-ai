import { useState, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { loginDict } from "../locales";
import PageBackground from "../components/login/PageBackground";
import BrandPanel from "../components/login/BrandPanel";
import LoginForm from "../components/login/LoginForm";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const [login, setLoginValue] = useState("");
  const [password, setPasswordValue] = useState("");
  const [pwVisible, setPwVisible] = useState(false);
  const [remember, setRemember] = useState(false);
  const [focus, setFocus] = useState<"login" | "pw" | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const { lang, setLang, t } = useLang(loginDict);

  const setLogin = (v: string) => {
    setLoginValue(v);
    setError(false);
  };
  const setPassword = (v: string) => {
    setPasswordValue(v);
    setError(false);
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
    setTimeout(() => navigate("/chat"), 3000);
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter") submit();
  };

  return (
    <div className={styles.page}>
      <PageBackground />

      <div className={styles.card}>
        <BrandPanel t={t} />
        <LoginForm
          t={t}
          lang={lang}
          setLang={setLang}
          login={login}
          setLogin={setLogin}
          password={password}
          setPassword={setPassword}
          pwVisible={pwVisible}
          setPwVisible={setPwVisible}
          remember={remember}
          setRemember={setRemember}
          focus={focus}
          setFocus={setFocus}
          loading={loading}
          error={error}
          submit={submit}
          onKey={onKey}
        />
      </div>
    </div>
  );
}
