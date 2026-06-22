import { GoSidebarCollapse, GoSidebarExpand } from "react-icons/go";
import styles from "./SidebarToggle.module.css";

interface SidebarToggleProps {
  open: boolean;
  onToggle: () => void;
  left: number;
}

// Sidebar'ni ochish/yopish tugmasi — har doim panel chegarasida "suzib" turadi.
// Sidebar ichida emas (tashqarida) joylashgani uchun ikkita holatda ham
// (ochiq/yopiq) xuddi shu joyda turadi, faqat sidebar kengligi o'zgarganda
// chap chegara bilan birga silliq suriladi (left transition).
export default function SidebarToggle({ open, onToggle, left }: SidebarToggleProps) {
  return (
    <button
      onClick={onToggle}
      title={open ? "Panelni yig'ish" : "Panelni ochish"}
      aria-label={open ? "Panelni yig'ish" : "Panelni ochish"}
      className={styles.toggle}
      style={{ left: `${left}px` }}
    >
      <span key={open ? "collapse" : "expand"} className={styles.icon}>
        {open ? <GoSidebarCollapse size={16} /> : <GoSidebarExpand size={16} />}
      </span>
    </button>
  );
}
