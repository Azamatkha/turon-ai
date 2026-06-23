import { ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IoMdChatboxes } from "react-icons/io";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { AdminView } from "../../types/admin";
import { admin } from "../../locales";
import { fetchMe, logout, type Me } from "../../services/authService";
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
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);

  // Tizimga kirgan adminni real bazadan olamiz (qattiq yozilgan ism o'rniga)
  useEffect(() => {
    fetchMe().then(setMe).catch(() => navigate("/login"));
  }, [navigate]);

  const meName = me?.full_name || "Admin";
  const meHandle = me ? "@" + me.username : "";
  const meInitial = meName.charAt(0).toUpperCase();

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

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

        {/* Chat sahifasiga qaytish */}
        <HButton
          onClick={() => navigate("/")}
          className={`${styles.navItem} ${styles.navItemInactive}`}
          baseStyle={{}}
          hoverStyle={{ background: "rgba(255,255,255,.06)", color: "#fff" }}
        >
          <span className={styles.navIcon}><IoMdChatboxes size={20} /></span>
          <span className={styles.navLabel}>Chatga o‘tish</span>
        </HButton>
      </nav>

      <div className={styles.footer}>
        <div className={styles.footerAvatar}>{meInitial}</div>
        <div className={styles.footerMeta}>
          <div className={styles.footerName}>{meName}</div>
          <div className={styles.footerRole}>{meHandle || admin.superAdmin}</div>
        </div>
        <button onClick={doLogout} title={admin.logout} aria-label={admin.logout} className={styles.logoutBtn}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
        </button>
      </div>
    </aside>
  );
}
