import { Link } from "react-router-dom";
import DotField from "../components/DotField";
import Logo from "../components/common/Logo";

const ACTION_STYLE = {
  position: "relative",
  zIndex: 1,
  marginTop: 20,
  padding: "12px 26px",
  borderRadius: 14,
  border: "none",
  background: "linear-gradient(135deg, #4059BE, #193070)",
  color: "#fff",
  fontWeight: 600,
  fontSize: 15.5,
  fontFamily: "inherit",
  cursor: "pointer",
  textDecoration: "none",
  boxShadow: "0 10px 26px rgba(25, 48, 112, 0.3)",
} as const;

interface Props {
  code?: string;
  title?: string;
  message?: string;
  // Berilsa — "Bosh sahifaga" havolasi o'rniga shu tugma chiqadi
  actionLabel?: string;
  onAction?: () => void;
}

// 404 — mavjud bo'lmagan sahifa (dot-field fon bilan).
// Xuddi shu dizayn tasdiqlanmagan user sahifasida ham ishlatiladi (UnverifiedPage).
export default function NotFoundPage({
  code = "404",
  title = "Sahifa topilmadi",
  message = "Siz qidirgan sahifa mavjud emas yoki ko‘chirilgan bo‘lishi mumkin.",
  actionLabel,
  onAction,
}: Props) {
  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        background: "#F8FAFC",
        color: "#193070",
        textAlign: "center",
        padding: 24,
        overflow: "hidden",
      }}
    >
      {/* interaktiv nuqta-to'r foni (login/admin sahifalaridagidek) */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0, opacity: 0.55, pointerEvents: "none" }} aria-hidden="true">
        <DotField
          dotRadius={3.5}
          dotSpacing={26}
          bulgeOnly
          bulgeStrength={18}
          cursorRadius={220}
          glowRadius={160}
          gradientFrom="#dbe0e7"
          gradientTo="#cfd6df"
          glowColor="rgba(64,89,190,0.07)"
        />
      </div>

      <div style={{ position: "relative", zIndex: 1, color: "#4059BE", marginBottom: 2 }}>
        <Logo size={52} />
      </div>

      <div
        style={{
          position: "relative",
          zIndex: 1,
          fontSize: "clamp(120px, 24vw, 210px)",
          fontWeight: 900,
          lineHeight: 0.9,
          letterSpacing: -8,
          background: "linear-gradient(160deg, #4059BE 0%, #193070 60%, #0d2747 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
          textShadow: "0 24px 60px rgba(25,48,112,.2)",
        }}
      >
        {code}
      </div>

      <div style={{ position: "relative", zIndex: 1, fontSize: 22, fontWeight: 700, marginTop: -4 }}>
        {title}
      </div>
      <div style={{ position: "relative", zIndex: 1, fontSize: 15.5, color: "#5b7180", maxWidth: 380, lineHeight: 1.5 }}>
        {message}
      </div>

      {onAction ? (
        <button type="button" onClick={onAction} style={ACTION_STYLE}>
          {actionLabel}
        </button>
      ) : (
        <Link to="/" style={ACTION_STYLE}>
          Bosh sahifaga qaytish
        </Link>
      )}
    </div>
  );
}
