import HButton from "../common/HButton";
import { admin } from "../../locales";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  onUsers: boolean;
  search: string;
  setSearch: (v: string) => void;
  onAddUser: () => void;
}

export default function PageHeader({ onUsers, search, setSearch, onAddUser }: PageHeaderProps) {
  const subtitle = onUsers
    ? admin.usersSubtitle
    : admin.overview + new Date().toLocaleDateString("uz-UZ", { weekday: "long", month: "long", day: "numeric" });

  return (
    <header className={styles.header}>
      <div>
        <div className={styles.title}>{onUsers ? admin.usersTitle : admin.dashboardTitle}</div>
        <div className={styles.subtitle}>{subtitle}</div>
      </div>
      <div className={styles.actions}>
        {onUsers && (
          <div className={styles.searchBox}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9aafb8" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            <input className={styles.searchInput} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={admin.searchUsersPh} />
          </div>
        )}
        <HButton onClick={onAddUser} className={styles.addBtn} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 8px 20px rgba(23, 63, 115,.3)" }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          {admin.addUser}
        </HButton>
      </div>
    </header>
  );
}
