import { ReactNode } from "react";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { AdminView } from "../../types/admin";
import { admin } from "../../locales";
import styles from "./Sidebar.module.css";

interface NavItem {
  id: AdminView;
  label: string;
  icon: ReactNode;
  badge?: string;
}

interface SidebarProps {
  view: AdminView;
  setView: (v: AdminView) => void;
  usersCount: number;
}

export default function Sidebar({ view, setView, usersCount }: SidebarProps) {
  const navItems: NavItem[] = [
    {
      id: "dashboard",
      label: admin.dashboardNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>,
    },
    {
      id: "users",
      label: admin.usersNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
      badge: String(usersCount),
    },
  ];

  return (
    <aside className={styles.aside}>
      <div className={styles.brandRow}>
        <div className={styles.logoIcon}><Logo size={30} /></div>
        <div>
          <div className={styles.brandName}>Turon<span className={styles.brandNameAi}> AI</span></div>
          <div className={styles.panelLabel}>{admin.panelLabel}</div>
        </div>
      </div>

      <nav className={styles.nav}>
        {navItems.map((item) => {
          const act = view === item.id;
          return (
            <HButton
              key={item.id}
              onClick={() => setView(item.id)}
              className={`${styles.navItem} ${act ? styles.navItemActive : styles.navItemInactive}`}
              baseStyle={{}}
              hoverStyle={act ? {} : { background: "rgba(255,255,255,.06)", color: "#fff" }}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
              {item.badge && <span className={styles.navBadge}>{item.badge}</span>}
            </HButton>
          );
        })}
      </nav>

      <div className={styles.footer}>
        <div className={styles.footerAvatar}>M</div>
        <div className={styles.footerMeta}>
          <div className={styles.footerName}>Malika Yusupova</div>
          <div className={styles.footerRole}>{admin.superAdmin}</div>
        </div>
      </div>
    </aside>
  );
}
