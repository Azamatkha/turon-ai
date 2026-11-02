import { platformsUrl } from "../../services/authService";
import styles from "./PlatformsButton.module.css";

// "Platformalar" ikonkasi — portal sahifasidagi tugmadagi SVG'ning AYNAN
// nusxasi (4 kvadrat, chiziq 2). RxDashboard ishlatilmaydi: u 15x15 to'r
// uchun chizilgan ingichka ikonka, 16px da xira va mayda ko'rinardi.
const platformsIcon = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="3" y="3" width="7" height="7" rx="2" />
    <rect x="14" y="3" width="7" height="7" rx="2" />
    <rect x="3" y="14" width="7" height="7" rx="2" />
    <rect x="14" y="14" width="7" height="7" rx="2" />
  </svg>
);

interface Props {
  label: string;
  // Tor joy uchun (yig'ilgan sidebar) — faqat ikonka, matn tooltip'da
  iconOnly?: boolean;
  className?: string;
}

// "Platformalar" — Turon AI portalidagi platformalar sahifasiga havola.
// Chat sidebar'ida va login sahifasida ishlatiladi. Portal manzili
// sozlanmagan bo'lsa (VITE_TURON_PORTAL_URL yo'q) hech narsa chizilmaydi.
export default function PlatformsButton({ label, iconOnly, className }: Props) {
  const href = platformsUrl();
  if (!href) return null;

  return (
    <a
      href={href}
      data-tip={iconOnly ? label : undefined}
      aria-label={iconOnly ? label : undefined}
      className={[styles.btn, iconOnly && styles.iconOnly, className].filter(Boolean).join(" ")}
    >
      {platformsIcon}
      {!iconOnly && <span>{label}</span>}
    </a>
  );
}
