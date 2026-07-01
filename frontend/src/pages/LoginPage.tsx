import { useState, KeyboardEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { loginDict } from "../locales";
import { login as loginRequest, isAuthenticated } from "../services/authService";
import PageBackground from "../components/login/PageBackground";
import BrandPanel from "../components/login/BrandPanel";
import LoginForm from "../components/login/LoginForm";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const [login, setLoginValue] = useState("");
  const [password, setPasswordValue] = useState("");
  const [pwVisible, setPwVisible] = useState(false);
  const [focus, setFocus] = useState<"login" | "pw" | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const { lang, setLang, t } = useLang(loginDict);

  // Allaqachon login qilingan bo'lsa — to'g'ridan-to'g'ri bosh sahifaga
  if (isAuthenticated()) return <Navigate to="/" replace />;

  const setLogin = (v: string) => {
    setLoginValue(v);
    setError(false);
  };
  const setPassword = (v: string) => {
    setPasswordValue(v);
    setError(false);
  };

  const submit = async () => {
    if (loading) return;
    if (!login.trim() || !password.trim()) {
      setError(true);
      return;
    }
    setLoading(true);
    setError(false);
    try {
      await loginRequest(login, password);
      navigate("/");
    } catch {
      setError(true);
      setLoading(false);
    }
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
