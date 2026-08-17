import { ReactNode, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import { PRIMARY, getSideTokens } from "../chat/theme";
import { useTheme } from "../../contexts/ThemeContext";
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
  // Ko'rib chiqilmagan murojaatlar soni (0 bo'lsa belgi ko'rinmaydi)
  newReportsCount: number;
  collapsed: boolean;
  t: AdminStrings;
}

export default function Sidebar({ view, setView, usersCount, newReportsCount, collapsed, t: admin }: SidebarProps) {
  const navigate = useNavigate();
  // Ranglar chat sidebar'i bilan AYNAN bir manbadan (`chat/theme.ts`) keladi —
  // ikki panel bir xil ko'rinishi kerak, faqat ichidagi funksiyalar farq qiladi.
  const { theme } = useTheme();
  const side = getSideTokens(theme === "dark");
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
      id: "reports",
      label: admin.reportsNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="15" x2="12" y2="15" /></svg>,
      badge: newReportsCount > 0 ? String(newReportsCount) : undefined,
    },
    {
      id: "knowledgeList",
      label: admin.knowledgeNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>,
    },
    {
      id: "pdfUpload",
      label: admin.pdfNav,
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="9" y1="15" x2="15" y2="15" /></svg>,
    },
    {
      id: "apiDocs",
      label: "API",
      icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>,
    },
  ];

  return (
    <aside
      className={styles.aside}
      style={{
        width: collapsed ? 72 : 282,
        background: side.bg,
        color: side.fg,
        borderRight: "1px solid " + side.border,
      }}
    >
      <div
        className={styles.brandRow}
        style={collapsed ? { justifyContent: "center", padding: 0, borderBottomColor: side.border } : { borderBottomColor: side.border }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 38, height: 38, borderRadius: 10, color: PRIMARY, background: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,.18)", flex: "0 0 auto" }}><Logo size={collapsed ? 22 : 24} /></div>
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
              hoverStyle={act ? {} : { background: side.active, color: "#fff" }}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
              {!collapsed && item.badge && <span className={styles.navBadge}>{item.badge}</span>}
            </HButton>
          );
        })}

        {/* "Chatga o'tish" ATAYLAB bu yerda emas — u admin panelning BO'LIMI
            emas, boshqa sahifaga o'tish. Endi yuqori panelda, til va mavzu
            almashtirgichlar yonida ikonka tugma sifatida turadi
            (`PageHeader.tsx`), xuddi chat sahifasidagi "admin panel"
            tugmasining ko'zgusi kabi. */}
      </nav>

      <div className={styles.footer} style={{ position: "relative", borderTopColor: side.border }} ref={footerRef}>
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(241,243,251,.6)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ transform: menuOpen ? "rotate(180deg)" : "none", transition: "transform .18s ease" }}>
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
              boxShadow: "0 12px 32px rgba(15,23,42,.28)",
              zIndex: 20,
            }}
          >
            <div style={{ padding: "6px 10px 8px", borderBottom: "1px solid var(--adm-border-3)", marginBottom: 4 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--adm-text-strong)", whiteSpace: "nowrap" }}>{meName}</div>
              <div style={{ fontSize: 12.5, color: "var(--adm-text-muted-2)" }}>{meHandle}</div>
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
                fontSize: 14,
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
