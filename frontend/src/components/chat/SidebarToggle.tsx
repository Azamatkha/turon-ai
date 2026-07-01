import { GoSidebarCollapse, GoSidebarExpand } from "react-icons/go";
import styles from "./SidebarToggle.module.css";

interface SidebarToggleProps {
  open: boolean;
  onToggle: () => void;
  left: number;
  openLabel?: string;
  closedLabel?: string;
  isDark?: boolean;
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
  isDark = false,
}: SidebarToggleProps) {
  return (
    <button
      onClick={onToggle}
      data-tip={open ? openLabel : closedLabel}
      aria-label={open ? openLabel : closedLabel}
      className={styles.toggle}
      style={{
        left: `${left}px`,
        ...(isDark
          ? { background: "#1c3e56", borderColor: "rgba(255,255,255,.16)", color: "#e8eef2" }
          : {}),
      }}
    >
      <span key={open ? "collapse" : "expand"} className={styles.icon}>
        {open ? <GoSidebarCollapse size={16} /> : <GoSidebarExpand size={16} />}
      </span>
    </button>
  );
}
