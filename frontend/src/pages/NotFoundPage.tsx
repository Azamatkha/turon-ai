import { Link } from "react-router-dom";
import DotField from "../components/DotField";
import Logo from "../components/common/Logo";

// 404 — mavjud bo'lmagan sahifa (dot-field fon bilan)
export default function NotFoundPage() {
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
        background: "#eef1f5",
        color: "#173f73",
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
          glowColor="rgba(42,111,151,0.07)"
        />
      </div>

      <div style={{ position: "relative", zIndex: 1, color: "#2a6f97", marginBottom: 2 }}>
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
          background: "linear-gradient(160deg, #3a7ca5 0%, #173f73 60%, #0d2747 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
          textShadow: "0 24px 60px rgba(23,63,115,.2)",
        }}
      >
        404
      </div>

      <div style={{ position: "relative", zIndex: 1, fontSize: 21, fontWeight: 700, marginTop: -4 }}>
        Sahifa topilmadi
      </div>
      <div style={{ position: "relative", zIndex: 1, fontSize: 14.5, color: "#5b7180", maxWidth: 380, lineHeight: 1.5 }}>
        Siz qidirgan sahifa mavjud emas yoki ko‘chirilgan bo‘lishi mumkin.
      </div>

      <Link
        to="/"
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: 20,
          padding: "12px 26px",
          borderRadius: 14,
          background: "linear-gradient(135deg, #2a6f97, #173f73)",
          color: "#fff",
          fontWeight: 600,
          fontSize: 14.5,
          textDecoration: "none",
          boxShadow: "0 10px 26px rgba(23, 63, 115, 0.3)",
        }}
      >
        Bosh sahifaga qaytish
      </Link>
    </div>
  );
}
