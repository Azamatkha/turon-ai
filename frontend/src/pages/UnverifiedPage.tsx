import { useLang } from "../hooks/useLang";
import { chatStaticDict, loginDict } from "../locales";
import { logout, PORTAL_LOGIN_URL } from "../services/authService";
import InstructionVideo from "../components/common/InstructionVideo";
import NotFoundPage, { type QrItem } from "./NotFoundPage";

// Verifikatsiya qo'llanmasi — public/videos/ da; BASE_URL (/chat/) bilan birga
const VIDEO_SRC = `${import.meta.env.BASE_URL}videos/verification.mp4`;

// Android ilova (APK) — public/app/ da. Yangi versiya chiqqanda
// aihelp/aiapk/TuronAI.apk shu yerga qayta nusxalanadi.
// QR telefonda ochiladi, shuning uchun manzil to'liq (domen bilan) bo'lishi kerak.
const MOBILE_APP_DOWNLOAD_URL = `${window.location.origin}${import.meta.env.BASE_URL}app/TuronAI.apk`;

// QR o'rtasidagi Android belgisi: yashil doira ichida oq robot boshi
const ANDROID_LOGO =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' +
      '<circle cx="12" cy="12" r="12" fill="#3DDC84"/>' +
      '<path d="M5.5 16.5a6.5 6.5 0 0 1 13 0z" fill="#fff"/>' +
      '<path d="M8 9.2 6.8 7.4M16 9.2l1.2-1.8" stroke="#fff" stroke-width="1.2" stroke-linecap="round"/>' +
      '<circle cx="9.6" cy="13.6" r=".9" fill="#3DDC84"/>' +
      '<circle cx="14.4" cy="13.6" r=".9" fill="#3DDC84"/>' +
      "</svg>",
  );

// QR o'rtasidagi Telegram belgisi: qora doira ichida oq "qog'oz samolyot"
const TELEGRAM_LOGO =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' +
      '<circle cx="12" cy="12" r="12" fill="#000"/>' +
      '<path d="M17.6 7.2 5.9 11.6c-.6.2-.6.6 0 .8l2.9.9 1.1 3.5c.1.4.3.5.6.2l1.6-1.5 3 2.2c.5.3.9.1 1-.5l2-9.3c.2-.8-.3-1.2-.5-1z" fill="#fff"/>' +
      "</svg>",
  );

// Mobil ilovada verifikatsiyadan o'tmagan user saytga kirganda ko'rinadi.
// Dizayn 404 sahifasi bilan bir xil — faqat matn va tugma boshqa.
export default function UnverifiedPage() {
  const { t, lang } = useLang(loginDict);
  const S = chatStaticDict[lang];

  const onLogout = async () => {
    await logout();
    // To'liq sahifa almashtiriladi — portalning login sahifasiga
    window.location.assign(PORTAL_LOGIN_URL);
  };

  // Kompyuterida Telegram ochilmaydigan xodimlar telefon bilan skanerlaydi
  const qrCodes: QrItem[] = [
    {
      title: t.unverifiedQrTelegram,
      value: `https://t.me/${S.supportTelegramBot}`,
      caption: `@${S.supportTelegramBot}`,
      logo: TELEGRAM_LOGO,
    },
  ];
  // Ikkinchi QR — skanerlansa APK to'g'ridan-to'g'ri yuklanadi (faqat Android)
  qrCodes.push({
    title: t.unverifiedQrApp,
    value: MOBILE_APP_DOWNLOAD_URL,
    caption: "Android",
    logo: ANDROID_LOGO,
  });

  return (
    <NotFoundPage
      code={null}
      title={t.unverifiedTitle}
      message={t.unverifiedText}
      actionLabel={t.unverifiedLogout}
      onAction={onLogout}
      qrCodes={qrCodes}
      aside={
        <InstructionVideo
          src={VIDEO_SRC}
          nudge={t.unverifiedVideoNudge}
          playLabel={t.unverifiedVideoPlay}
          replayLabel={t.unverifiedVideoReplay}
          endedText={t.unverifiedVideoEnded}
        />
      }
      support={{
        phoneLabel: S.supportHint,
        phone: S.supportNumber,
      }}
    />
  );
}
