import { GoSidebarCollapse, GoSidebarExpand } from "react-icons/go";
import styles from "./SidebarToggle.module.css";

interface SidebarToggleProps {
  open: boolean;
  onToggle: () => void;
  left: number;
  openLabel?: string;
  closedLabel?: string;
}

// Sidebar'ni ochish/yopish tugmasi — har doim panel chegarasida "suzib" turadi.
// Sidebar ichida emas (tashqarida) joylashgani uchun ikkita holatda ham
// (ochiq/yopiq) xuddi shu joyda turadi, faqat sidebar kengligi o'zgarganda
// chap chegara bilan birga silliq suriladi (left transition).
export default function SidebarToggle({
  open,
  onToggle,
  left,
  openLabel = "Panelni yig'ish",
  closedLabel = "Panelni ochish",
}: SidebarToggleProps) {
  return (
    <button
      onClick={onToggle}
      data-tip={open ? openLabel : closedLabel}
      aria-label={open ? openLabel : closedLabel}
      className={`${styles.toggle} tip-right`}
      /* Faqat joylashuv inline — ranglar CSS mavzu tokenlaridan keladi
         (SidebarToggle.module.css). Shu sababli chat va admin panelida
         tugma bir xil ishlaydi, hech qanday `isDark` prop kerak emas. */
      style={{ left: `${left}px` }}
    >
      <span key={open ? "collapse" : "expand"} className={styles.icon}>
        {open ? <GoSidebarCollapse size={16} /> : <GoSidebarExpand size={16} />}
      </span>
    </button>
  );
}
