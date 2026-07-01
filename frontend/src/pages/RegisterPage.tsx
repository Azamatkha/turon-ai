import { useState, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { loginDict } from "../locales";
import PageBackground from "../components/login/PageBackground";
import BrandPanel from "../components/login/BrandPanel";
import RegisterForm from "../components/login/RegisterForm";
import { register as registerRequest } from "../services/authService";
import styles from "./LoginPage.module.css";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { lang, setLang, t } = useLang(loginDict);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [department, setDepartment] = useState("");
  const [password, setPassword] = useState("");
  const [pwVisible, setPwVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (loading) return;
    if (!fullName.trim() || !username.trim() || !password.trim()) {
      setError("Iltimos, barcha majburiy maydonlarni to‘ldiring.");
      return;
    }
    if (username.trim().length < 4) {
      setError("Login kamida 4 ta belgidan iborat bo‘lsin.");
      return;
    }
    const strongPassword = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
    if (!strongPassword.test(password)) {
      setError("Parol kamida 8 ta belgi bo‘lib, katta harf, kichik harf, raqam va belgi (masalan: Admin123!) bo‘lishi kerak.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await registerRequest({
        username: username.trim(),
        full_name: fullName.trim(),
        department: department.trim() || undefined,
        password,
      });
      navigate("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Xatolik yuz berdi");
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
        <RegisterForm
          lang={lang}
          setLang={setLang}
          fullName={fullName}
          setFullName={setFullName}
          username={username}
          setUsername={setUsername}
          department={department}
          setDepartment={setDepartment}
          password={password}
          setPassword={setPassword}
          pwVisible={pwVisible}
          setPwVisible={setPwVisible}
          loading={loading}
          error={error}
          submit={submit}
          onKey={onKey}
        />
      </div>
    </div>
  );
}
