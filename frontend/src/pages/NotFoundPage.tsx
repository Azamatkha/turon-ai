import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import DotField from "../components/DotField";
import Logo from "../components/common/Logo";
import styles from "./NotFoundPage.module.css";

const ACTION_STYLE = {
  position: "relative",
  zIndex: 1,
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
  // null — katta raqam ko'rsatilmaydi, uning o'rniga sarlavhaning o'zi animatsiya bilan chiqadi
  code?: string | null;
  title?: string;
  message?: string;
  // Berilsa — "Bosh sahifaga" havolasi o'rniga shu tugma chiqadi
  actionLabel?: string;
  onAction?: () => void;
  // Berilsa — yordam telefoni tugmasi chiqadi
  support?: SupportContacts;
  // Berilsa — telefon bilan skanerlash uchun QR kodlar (yordam raqamidan tepada)
  qrCodes?: QrItem[];
}

export interface QrItem {
  title: string;
  value: string;
  // QR ostidagi qisqa yozuv (masalan, "@turonai_help_bot")
  caption?: string;
  // O'rtadagi logotip (data-URI). Xato tuzatish "H" darajada — logotip
  // QR'ning bir qismini yopsa ham skanerlanadi.
  logo?: string;
}

export interface SupportContacts {
  phoneLabel: string;
  phone: string;
}

// 404 — mavjud bo'lmagan sahifa (dot-field fon bilan).
// Xuddi shu dizayn tasdiqlanmagan user sahifasida ham ishlatiladi (UnverifiedPage).
export default function NotFoundPage({
  code = "404",
  title = "Sahifa topilmadi",
  message = "Siz qidirgan sahifa mavjud emas yoki ko‘chirilgan bo‘lishi mumkin.",
  actionLabel,
  onAction,
  support,
  qrCodes,
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
        // Tepa/past joy — burchakdagi logo va tugma kontentni bosib qolmasin
        padding: "84px 24px 96px",
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

      {/* Logo — chap yuqori burchakda */}
      <div className={styles.cornerLogo}>
        <Logo size={44} />
      </div>

      {code ? (
        <>
          {/* Har bir raqam alohida span — o'z animatsiyasi bilan (CSS'dagi --i navbat) */}
          <div className={styles.code} role="img" aria-label={code}>
            {code.split("").map((ch, i) => (
              <span key={i} className={styles.digitWrap} style={{ "--i": i } as CSSProperties} aria-hidden="true">
                <span className={styles.digit}>{ch}</span>
              </span>
            ))}
          </div>

          <div style={{ position: "relative", zIndex: 1, fontSize: 22, fontWeight: 700, marginTop: 20 }}>
            {title}
          </div>
        </>
      ) : (
        // Raqam yo'q — sarlavhaning o'zi katta va har bir so'z raqamlardek
        // navbat bilan tushib, keyin sekin "suzadi"
        <h1 className={styles.headline} aria-label={title}>
          {title.split(" ").map((word, i) => (
            <span key={i} className={styles.digitWrap} style={{ "--i": i } as CSSProperties} aria-hidden="true">
              <span className={`${styles.digit} ${styles.headlineWord}`}>{word}</span>
            </span>
          ))}
        </h1>
      )}
      <div style={{ position: "relative", zIndex: 1, fontSize: 15.5, color: "#5b7180", maxWidth: 440, lineHeight: 1.5 }}>
        {message}
      </div>

      {/* QR kodlar — matn ostida, yordam raqamidan tepada (kompyuterida Telegram yo'q xodimlar telefon bilan skanerlaydi) */}
      {qrCodes && qrCodes.length > 0 && (
        <div className={styles.qrList}>
          {qrCodes.map((qr) => (
            // Oddiy quti, havola EMAS: QR telefon kamerasi bilan skanerlanadi,
            // kompyuterda bosilganda Telegram sahifasi ochilib ketmasin
            <div key={qr.value} className={styles.qrCard}>
              <span className={styles.qrTitle}>{qr.title}</span>
              <QRCodeSVG
                value={qr.value}
                size={200}
                level="H"
                marginSize={0}
                fgColor="#000000"
                bgColor="#FFFFFF"
                title={qr.title}
                imageSettings={qr.logo ? { src: qr.logo, height: 46, width: 46, excavate: true } : undefined}
              />
              {qr.caption && <span className={styles.qrCaption}>{qr.caption}</span>}
            </div>
          ))}
        </div>
      )}

      {support && (
        <div className={styles.support}>
          {/* Telefon — bosilsa qo'ng'iroq ilovasi ochiladi */}
          <a href={`tel:${support.phone}`} className={styles.supportBtn}>
            <span className={styles.supportIcon} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" /></svg>
            </span>
            <span className={styles.supportText}>
              <span className={styles.supportLabel}>{support.phoneLabel}</span>
              <span className={styles.supportValue}>{support.phone}</span>
            </span>
          </a>
        </div>
      )}

      {/* Asosiy tugma — chap pastki burchakda */}
      <div className={styles.cornerAction}>
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
    </div>
  );
}
