import { ReactNode, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IoMdChatboxes } from "react-icons/io";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import { PRIMARY } from "../chat/theme";
import type { AdminView } from "../../types/admin";
import type { AdminStrings } from "../../types/i18n";
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
  collapsed: boolean;
  t: AdminStrings;
}

export default function Sidebar({ view, setView, usersCount, collapsed, t: admin }: SidebarProps) {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const footerRef = useRef<HTMLDivElement>(null);

  // Tashqariga bosilganda menyuni yopish
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (footerRef.current && !footerRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

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
    {
      id: "knowledgeList",
      label: admin.knowledgeNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>,
    },
  ];

  return (
    <aside
      className={styles.aside}
      style={{ width: collapsed ? 76 : 248, transition: "width .2s ease" }}
    >
      <div
        className={styles.brandRow}
        style={collapsed ? { justifyContent: "center", padding: 0 } : undefined}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 38, height: 38, borderRadius: 10, color: PRIMARY, background: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,.22)" }}><Logo size={collapsed ? 22 : 24} /></div>
        {!collapsed && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className={styles.brandName}>Turon<span className={styles.brandNameAi}> AI</span></div>
            <div className={styles.panelLabel}>{admin.panelLabel}</div>
          </div>
        )}
      </div>

      <nav className={styles.nav}>
        {navItems.map((item) => {
          const act = view === item.id;
          return (
            <HButton
              key={item.id}
              onClick={() => setView(item.id)}
              className={`${styles.navItem} ${act ? styles.navItemActive : styles.navItemInactive}`}
              baseStyle={collapsed ? { justifyContent: "center" } : {}}
              hoverStyle={act ? {} : { background: "rgba(255,255,255,.06)", color: "#fff" }}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
              {!collapsed && item.badge && <span className={styles.navBadge}>{item.badge}</span>}
            </HButton>
          );
        })}

        <HButton
          onClick={() => navigate("/")}
          className={`${styles.navItem} ${styles.navItemInactive}`}
          baseStyle={collapsed ? { justifyContent: "center" } : {}}
          hoverStyle={{ background: "rgba(255,255,255,.06)", color: "#fff" }}
        >
          <span className={styles.navIcon}><IoMdChatboxes size={20} /></span>
          {!collapsed && <span className={styles.navLabel}>{admin.chatNav}</span>}
        </HButton>
      </nav>

      <div className={styles.footer} style={{ position: "relative" }} ref={footerRef}>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            width: "100%",
            justifyContent: collapsed ? "center" : "flex-start",
            background: "transparent",
            border: "none",
            padding: 0,
            cursor: "pointer",
            color: "inherit",
          }}
        >
          <div className={styles.footerAvatar}>{meInitial}</div>
          {!collapsed && (
            <div className={styles.footerMeta} style={{ textAlign: "left" }}>
              <div className={styles.footerName}>{meName}</div>
              <div className={styles.footerRole}>{meHandle || admin.superAdmin}</div>
            </div>
          )}
          {!collapsed && (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(238,242,239,.6)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transform: menuOpen ? "rotate(180deg)" : "none", transition: "transform .18s ease" }}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          )}
        </button>

        {menuOpen && (
          <div
            style={{
              position: "absolute",
              bottom: "calc(100% + 8px)",
              left: 12,
              minWidth: 180,
              background: "var(--adm-card)",
              border: "1px solid var(--adm-border)",
              borderRadius: 12,
              padding: 6,
              boxShadow: "0 12px 32px rgba(13,33,45,.28)",
              zIndex: 20,
            }}
          >
            <div style={{ padding: "6px 10px 8px", borderBottom: "1px solid var(--adm-border-3)", marginBottom: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--adm-text-strong)", whiteSpace: "nowrap" }}>{meName}</div>
              <div style={{ fontSize: 11.5, color: "var(--adm-text-muted-2)" }}>{meHandle}</div>
            </div>
            <button
              onClick={doLogout}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--adm-danger-bg)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 9,
                width: "100%",
                padding: "9px 10px",
                border: "none",
                background: "transparent",
                color: "var(--adm-danger)",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
              {admin.logout}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
