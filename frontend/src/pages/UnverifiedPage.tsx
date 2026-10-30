import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { chatStaticDict, loginDict } from "../locales";
import { logout } from "../services/authService";
import NotFoundPage from "./NotFoundPage";

// Mobil ilovada verifikatsiyadan o'tmagan user saytga kirganda ko'rinadi.
// Dizayn 404 sahifasi bilan bir xil — faqat matn va tugma boshqa.
export default function UnverifiedPage() {
  const navigate = useNavigate();
  const { t, lang } = useLang(loginDict);
  const S = chatStaticDict[lang];

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <NotFoundPage
      code="403"
      title={t.unverifiedTitle}
      message={t.unverifiedText}
      actionLabel={t.unverifiedLogout}
      onAction={onLogout}
      support={{
        phoneLabel: S.supportHint,
        phone: S.supportNumber,
        botLabel: S.supportTelegramLabel,
        bot: S.supportTelegramBot,
      }}
    />
  );
}
