import { useState, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { loginDict } from "../locales";
import type { Lang } from "../types/lang";
import PageBackground from "../components/login/PageBackground";
import BrandPanel from "../components/login/BrandPanel";
import RegisterForm from "../components/login/RegisterForm";
import { register as registerRequest, ApiError } from "../services/authService";
import styles from "./LoginPage.module.css";

// Ro'yxatdan o'tish xatolari — 3 tilda, aniq va tushunarli
const ERR: Record<Lang, {
  required: string; usernameShort: string; passwordShort: string;
  mismatch: string; usernameTaken: string; generic: string;
}> = {
  uz: {
    required: "Iltimos, barcha majburiy maydonlarni to‘ldiring.",
    usernameShort: "Login kamida 4 ta belgidan iborat bo‘lsin.",
    passwordShort: "Parol kamida 4 ta belgidan iborat bo‘lsin.",
    mismatch: "Parollar bir xil emas.",
    usernameTaken: "Bu login allaqachon band. Boshqa login tanlang.",
    generic: "Xatolik yuz berdi. Qayta urinib ko‘ring.",
  },
  uz_cyrl: {
    required: "Илтимос, барча мажбурий майдонларни тўлдиринг.",
    usernameShort: "Логин камида 4 та белгидан иборат бўлсин.",
    passwordShort: "Парол камида 4 та белгидан иборат бўлсин.",
    mismatch: "Пароллар бир хил эмас.",
    usernameTaken: "Бу логин аллақачон банд. Бошқа логин танланг.",
    generic: "Хатолик юз берди. Қайта уриниб кўринг.",
  },
  ru: {
    required: "Пожалуйста, заполните все обязательные поля.",
    usernameShort: "Логин должен содержать минимум 4 символа.",
    passwordShort: "Пароль должен содержать минимум 4 символа.",
    mismatch: "Пароли не совпадают.",
    usernameTaken: "Этот логин уже занят. Выберите другой.",
    generic: "Произошла ошибка. Попробуйте снова.",
  },
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const { lang, setLang, t } = useLang(loginDict);
  const err = ERR[lang];
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [department, setDepartment] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (loading) return;
    if (!fullName.trim() || !username.trim() || !password.trim()) {
      setError(err.required);
      return;
    }
    if (username.trim().length < 4) {
      setError(err.usernameShort);
      return;
    }
    if (password.length < 4) {
      setError(err.passwordShort);
      return;
    }
    if (password !== confirmPassword) {
      setError(err.mismatch);
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
      setError(e instanceof ApiError && e.status === 409 ? err.usernameTaken : err.generic);
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
          confirmPassword={confirmPassword}
          setConfirmPassword={setConfirmPassword}
          loading={loading}
          error={error}
          submit={submit}
          onKey={onKey}
        />
      </div>
    </div>
  );
}
