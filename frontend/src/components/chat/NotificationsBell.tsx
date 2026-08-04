import { useCallback, useEffect, useState } from "react";
import { IoNotificationsOutline } from "react-icons/io5";
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

  const format = useCallback(
    (n: ApiNotification) => ({ title: titleFor(n, s), body: bodyFor(n) }),
    [s]
  );
  const { unread, items, loading, refresh, markRead, markAllRead, requestDesktop } =
    useNotifications(format);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    // Ro'yxat faqat panel ochilganda yuklanadi — polling faqat sonni so'raydi
    if (next) void refresh();
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const enableDesktop = async () => {
    const result = await requestDesktop();
    setPerm(result);
  };

  return (
    <div className={styles.wrap}>
      <HButton
        onClick={toggle}
        data-tip={s.notifications}
        aria-label={s.notifications}
        className={headerStyles.adminBtn}
        baseStyle={{
          background: isDark ? "rgba(255,255,255,.08)" : "#fff",
          border: "1px solid " + (isDark ? "rgba(255,255,255,.16)" : "#dde2dc"),
          color: isDark ? "#e8eef2" : "#173f73",
          position: "relative",
        }}
        hoverStyle={{
          background: isDark ? "rgba(255,255,255,.16)" : "#eef3f6",
          transform: "translateY(-1px)",
        }}
      >
        <IoNotificationsOutline size={19} />
        {unread > 0 && (
          <span className={styles.badge}>{unread > 99 ? "99+" : unread}</span>
        )}
      </HButton>

      {open && (
        <>
          {/* Tashqariga bosilganda yopiladi */}
          <div className={styles.backdrop} onClick={() => setOpen(false)} />
          <div
            className={styles.panel}
            style={{ background: tk.card, border: "1px solid " + tk.cardBorder }}
          >
            <div className={styles.head} style={{ borderColor: tk.cardBorder }}>
              <span className={styles.headTitle} style={{ color: tk.strong }}>
                {s.notifications}
              </span>
              {unread > 0 && (
                <button
                  type="button"
                  className={styles.linkBtn}
                  style={{ color: tk.muted }}
                  onClick={() => void markAllRead()}
                >
                  {s.notifMarkAll}
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
              <div className={styles.optInMuted} style={{ color: tk.muted }}>
                {s.notifDesktopBlocked}
              </div>
            )}

            <div className={styles.list}>
              {!loading && items.length === 0 && (
                <div className={styles.empty} style={{ color: tk.muted }}>
                  {s.notifEmpty}
                </div>
              )}
              {items.map((n) => (
                <div
                  key={n.id}
                  className={styles.row}
                  style={{ borderColor: tk.cardBorder }}
                >
                  <span
                    className={n.is_read ? styles.dotRead : styles.dotUnread}
                    aria-hidden="true"
                  />
                  <div className={styles.rowBody}>
                    <div className={styles.rowTitle} style={{ color: tk.strong }}>
                      {titleFor(n, s)}
                    </div>
                    {bodyFor(n) && (
                      <div className={styles.rowText} style={{ color: tk.muted }}>
                        {bodyFor(n)}
                      </div>
                    )}
                    <div className={styles.rowTime} style={{ color: tk.disc }}>
                      {relTime(n.created_at, s)}
                    </div>
                  </div>
                  {!n.is_read && (
                    <button
                      type="button"
                      className={styles.readBtn}
                      data-tip={s.notifMarkRead}
                      aria-label={s.notifMarkRead}
                      style={{ color: tk.muted }}
                      onClick={() => void markRead(n.id)}
                    >
                      ✓
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
