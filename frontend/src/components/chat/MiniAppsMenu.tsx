import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { MdApps } from "react-icons/md";
import HButton from "../common/HButton";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import headerStyles from "./ChatHeader.module.css";
import styles from "./MiniAppsMenu.module.css";

/** Menyudagi bitta mini-ilova. Yangi ilova qo'shish = ChatHeader'dagi
 *  ro'yxatga bitta yozuv qo'shish (ikonka + nom + ochish funksiyasi). */
export interface MiniApp {
  id: string;
  label: string;
  icon: ReactNode;
  onOpen: () => void;
}

interface MiniAppsMenuProps {
  apps: MiniApp[];
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
}

export default function MiniAppsMenu({ apps, tk, isDark, s }: MiniAppsMenuProps) {
  const [open, setOpen] = useState(false);
  // Panel <body> ga portal qilinadi (NotificationsBell bilan bir xil sabab) —
  // joyi tugma koordinatasidan hisoblanadi.
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const place = useCallback(() => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    // Tor ekranda panel ekrandan chiqib ketmasin — o'ngdan kamida 8px
    setPos({ top: rect.bottom + 10, right: Math.max(8, window.innerWidth - rect.right) });
  }, []);

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    place();
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (wrapRef.current?.contains(target)) return; // tugmani toggle o'zi hal qiladi
      setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    window.addEventListener("resize", place);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("resize", place);
    };
  }, [open, place]);

  const launch = (app: MiniApp) => {
    setOpen(false);
    app.onOpen();
  };

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <HButton
        onClick={toggle}
        data-tip={s.miniApps}
        aria-label={s.miniApps}
        aria-expanded={open}
        aria-haspopup="true"
        className={`${headerStyles.adminBtn} tu-shiny tu-shiny-always`}
        baseStyle={{
          border: "1px solid var(--tu-glass-border)",
          color: isDark ? "#E2E8F0" : "#193070",
          backdropFilter: "var(--tu-glass-blur)",
          WebkitBackdropFilter: "var(--tu-glass-blur)",
        }}
        /* Fon hover'i .adminBtn:hover da (ChatHeader.module.css dagi izoh) */
        hoverStyle={{ transform: "translateY(-1px)" }}
      >
        <MdApps size={21} />
      </HButton>

      {open &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className={styles.panel}
            role="menu"
            aria-label={s.miniApps}
            style={{
              top: pos.top,
              right: pos.right,
              background: tk.card,
              border: "1px solid " + tk.cardBorder,
            }}
          >
            <div className={styles.head} style={{ color: tk.strong, borderColor: tk.cardBorder }}>
              {s.miniApps}
            </div>
            <div className={styles.grid}>
              {apps.map((app) => (
                <button
                  key={app.id}
                  type="button"
                  role="menuitem"
                  className={styles.tile}
                  style={{ color: tk.strong }}
                  onClick={() => launch(app)}
                >
                  <span className={styles.tileIcon} style={{ color: isDark ? "#C7D2FE" : "#193070" }}>
                    {app.icon}
                  </span>
                  <span className={styles.tileLabel}>{app.label}</span>
                </button>
              ))}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
