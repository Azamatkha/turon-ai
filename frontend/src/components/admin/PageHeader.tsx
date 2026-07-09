import HButton from "../common/HButton";
import type { AdminView } from "../../types/admin";
import { admin } from "../../locales";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  view: AdminView;
  search: string;
  setSearch: (v: string) => void;
  onAddUser: () => void;
}

const TITLES: Record<AdminView, string> = {
  dashboard: admin.dashboardTitle,
  users: admin.usersTitle,
  knowledgeList: admin.knowledgeTitle,
};

export default function PageHeader({ view, search, setSearch, onAddUser }: PageHeaderProps) {
  const onUsers = view === "users";
  // "Foydalanuvchi qo'shish" tugmasi faqat dashboard/users sahifalarida
  const showAddUser = view === "dashboard" || view === "users";
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.title}>{TITLES[view]}</div>
      </div>
      <div className={styles.actions}>
        {onUsers && (
          <div className={styles.searchBox}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9aafb8" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            <input className={styles.searchInput} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={admin.searchUsersPh} />
          </div>
        )}
        {showAddUser && (
          <HButton onClick={onAddUser} className={styles.addBtn} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 8px 20px rgba(23, 63, 115,.3)" }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            {admin.addUser}
          </HButton>
        )}
      </div>
    </header>
  );
}
