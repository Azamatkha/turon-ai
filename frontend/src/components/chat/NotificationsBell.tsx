import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { MdMarkChatRead, MdNotificationsActive } from "react-icons/md";
import HButton from "../common/HButton";
import {
  desktopPermission,
  useNotifications,
} from "../../hooks/useNotifications";
import type { ApiNotification } from "../../services/notificationService";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import headerStyles from "./ChatHeader.module.css";
import styles from "./NotificationsBell.module.css";

interface NotificationsBellProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
}

// Bildirishnoma sarlavhasi turiga qarab tanlanadi — backend matn yubormaydi
function titleFor(n: ApiNotification, s: ChatStaticStrings): string {
  switch (n.type) {
    case "knowledge_updated":
      return s.notifKnowledgeUpdated;
    case "rates_updated":
      return s.notifRatesUpdated;
    case "report_new":
      return s.notifReportNew;
    default:
      return s.notifications;
  }
}

function bodyFor(n: ApiNotification): string {
  return n.params?.title ?? "";
}

/** Bildirishnoma bosilganda ochiladigan sahifa (bo'lmasa — null).
 *  Hozircha faqat murojaatlar: admin panelning o'sha murojaati ochiladi. */
function linkFor(n: ApiNotification): string | null {
  if (n.type === "report_new" && n.entity_id) {
    return `/admin/reports?report=${n.entity_id}`;
  }
  return null;
}

function relTime(iso: string, s: ChatStaticStrings): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "";
  const sec = Math.max(0, (Date.now() - t) / 1000);
  if (sec < 60) return s.notifTimeNow;
  if (sec < 3600) return s.notifMinAgo(Math.floor(sec / 60));
  if (sec < 86400) return s.notifHourAgo(Math.floor(sec / 3600));
  return s.notifDayAgo(Math.floor(sec / 86400));
}

export default function NotificationsBell({ tk, isDark, s }: NotificationsBellProps) {
  const [open, setOpen] = useState(false);
  const [perm, setPerm] = useState(desktopPermission());
  const [showHow, setShowHow] = useState(false);
  // Panel portal orqali <body> ga chiqadi — header'ning z-index qatlamiga
  // qamalib qolmasin. Shuning uchun joyi tugma koordinatasidan hisoblanadi.
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const format = useCallback(
    (n: ApiNotification) => ({ title: titleFor(n, s), body: bodyFor(n) }),
    [s]
  );
  const {
    unread,
    items,
    loading,
    refresh,
    markRead,
    markAllRead,
    requestDesktop,
  } = useNotifications(format);

  const place = useCallback(() => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPos({ top: rect.bottom + 10, right: window.innerWidth - rect.right });
  }, []);

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    place();
    // Foydalanuvchi brauzer sozlamalarida ruxsatni o'zgartirgan bo'lishi mumkin
    setPerm(desktopPermission());
    setOpen(true);
    // Ro'yxat faqat panel ochilganda yuklanadi — polling faqat sonni so'raydi
    void refresh();
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    // Tashqariga bosilganda yopiladi. Qoplama <div> ishlatilmaydi: u tugmani
    // ham to'sib qo'yardi va bosish ikki marta hisoblanardi.
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

  const enableDesktop = async () => {
    const result = await requestDesktop();
    setPerm(result);
  };

  // Havolali bildirishnoma bosilganda: o'qilgan deb belgilanadi va o'sha
  // obyektga (masalan murojaatga) o'tiladi.
  const openLink = (n: ApiNotification, href: string) => {
    if (!n.is_read) void markRead(n.id);
    setOpen(false);
    navigate(href);
  };

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <HButton
        onClick={toggle}
        data-tip={s.notifications}
        aria-label={s.notifications}
        className={headerStyles.adminBtn}
        baseStyle={{
          background: isDark ? "rgba(255,255,255,.08)" : "#fff",
          border: "1px solid " + (isDark ? "rgba(255,255,255,.16)" : "#CBD5E1"),
          color: isDark ? "#E2E8F0" : "#1E3A5F",
          position: "relative",
        }}
        hoverStyle={{
          background: isDark ? "rgba(255,255,255,.16)" : "#F1F5F9",
          transform: "translateY(-1px)",
        }}
      >
        {/* O'qilmagan bo'lsa qo'ng'iroq chayqaladi va belgi puls beradi */}
        <span className={unread > 0 ? styles.bellRing : undefined}>
          <MdNotificationsActive size={20} />
        </span>
        {unread > 0 && (
          <span className={styles.badge}>{unread > 99 ? "99+" : unread}</span>
        )}
      </HButton>

      {open &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className={styles.panel}
            style={{
              top: pos.top,
              right: pos.right,
              background: tk.card,
              border: "1px solid " + tk.cardBorder,
            }}
          >
            <div className={styles.head} style={{ borderColor: tk.cardBorder }}>
              <span className={styles.headTitle} style={{ color: tk.strong }}>
                {s.notifications}
              </span>
              {unread > 0 && (
                <button
                  type="button"
                  className={`${styles.markAllBtn} tip-end`}
                  data-tip={s.notifMarkAll}
                  aria-label={s.notifMarkAll}
                  style={{ color: tk.muted }}
                  onClick={() => void markAllRead()}
                >
                  <MdMarkChatRead size={17} />
                </button>
              )}
            </div>

            {perm === "default" && (
              <button
                type="button"
                className={styles.optIn}
                style={{ color: tk.strong, borderColor: tk.cardBorder }}
                onClick={() => void enableDesktop()}
              >
                {s.notifEnableDesktop}
              </button>
            )}
            {perm === "denied" && (
              <button
                type="button"
                className={styles.blocked}
                style={{ color: tk.muted, borderColor: tk.cardBorder }}
                onClick={() => setShowHow((v) => !v)}
              >
                <span className={styles.blockedRow}>
                  <span>{s.notifDesktopBlocked}</span>
                  <span className={styles.blockedHow}>{s.notifDesktopHow}</span>
                </span>
                {showHow && (
                  <>
                    <span className={styles.blockedSteps} style={{ color: tk.disc }}>
                      {s.notifDesktopSteps}
                    </span>
                    {/* Brauzer sozlamalarida saytni topish oson bo'lsin */}
                    <span className={styles.blockedSite} style={{ color: tk.strong }}>
                      {s.notifDesktopSiteLabel} {window.location.host}
                    </span>
                  </>
                )}
              </button>
            )}

            <div className={styles.list}>
              {!loading && items.length === 0 && (
                <div className={styles.empty} style={{ color: tk.muted }}>
                  {s.notifEmpty}
                </div>
              )}
              {items.map((n) => {
                const href = linkFor(n);
                // Butun qator bosiladi: havolasi bo'lsa o'sha sahifa ochiladi,
                // bo'lmasa shunchaki o'qilgan deb belgilanadi. Shu sababli
                // alohida ✓ tugmasi kerak emas — qator ham tozaroq ko'rinadi.
                return (
                  <button
                    key={n.id}
                    type="button"
                    className={styles.row}
                    style={{ borderColor: tk.cardBorder }}
                    onClick={() => (href ? openLink(n, href) : void markRead(n.id))}
                  >
                    <span
                      className={n.is_read ? styles.dotRead : styles.dotUnread}
                      aria-hidden="true"
                    />
                    <span className={styles.rowBody}>
                      <span className={styles.rowTop}>
                        <span className={styles.rowTitle} style={{ color: tk.strong }}>
                          {titleFor(n, s)}
                        </span>
                        <span className={styles.rowTime} style={{ color: tk.disc }}>
                          {relTime(n.created_at, s)}
                        </span>
                      </span>
                      {bodyFor(n) && (
                        <span className={styles.rowText} style={{ color: tk.muted }}>
                          {bodyFor(n)}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
