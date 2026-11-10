import { useCallback, useEffect, useState } from "react";
import { fmtDate, tgUserName } from "./TelegramBotView";
import { listTgMessages, type ApiTgMessage, type ApiTgUser } from "../../services/telegramBotService";
import type { AdminStrings } from "../../types/i18n";
import { useModalA11y } from "../../hooks/useModalA11y";
import styles from "./TelegramBotChatModal.module.css";

interface TelegramBotChatModalProps {
  user: ApiTgUser;
  t: AdminStrings;
  onClose: () => void;
}

const PAGE_SIZE = 50;

// Bitta userning yozishmalari: userdan — chapda, admin javobi — o'ngda.
// Backend yangisidan eskisiga beradi; "Oldingi xabarlar" keyingi sahifani tepaga qo'shadi.
export default function TelegramBotChatModal({ user, t: admin, onClose }: TelegramBotChatModalProps) {
  const [items, setItems] = useState<ApiTgMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const data = await listTgMessages(user.id, { page: p, size: PAGE_SIZE });
        // Ekranda eskisi tepada bo'lishi uchun teskari tartib
        const older = [...data.items].reverse();
        setItems((prev) => (p === 1 ? older : [...older, ...prev]));
        setTotal(data.total);
        setPage(p);
        setErr(null);
      } catch (e) {
        setErr((e instanceof Error && e.message) || admin.tgBotLoadError);
      } finally {
        setLoading(false);
      }
    },
    [user.id, admin.tgBotLoadError]
  );

  useEffect(() => {
    void load(1);
  }, [load]);

  const modalRef = useModalA11y<HTMLDivElement>(onClose);

  const contentLabel = (m: ApiTgMessage) => {
    if (m.content_type === "text") return null;
    const label = admin.tgBotContent[m.content_type] ?? m.content_type;
    return m.items > 1 ? `${label} · ${m.items}` : label;
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={admin.tgBotChatTitle}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <div>
            <div className={styles.title}>{tgUserName(user)}</div>
            <div className={styles.sub}>
              {admin.tgBotChatTitle}
              {user.username ? ` · @${user.username}` : ""}
              {user.phone ? ` · ${user.phone}` : ""}
            </div>
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="×">
            ×
          </button>
        </div>

        <div className={styles.body}>
          {err && <div className={styles.error}>{err}</div>}

          {items.length < total && (
            <button type="button" className={styles.olderBtn} onClick={() => void load(page + 1)} disabled={loading}>
              {admin.tgBotLoadOlder}
            </button>
          )}

          {!loading && items.length === 0 && !err && <div className={styles.empty}>{admin.tgBotChatEmpty}</div>}

          {items.map((m) => {
            const out = m.direction === "out";
            const kind = contentLabel(m);
            return (
              <div key={m.id} className={`${styles.msg} ${out ? styles.out : styles.inc}`}>
                <div className={styles.bubble}>
                  {kind && <div className={styles.kind}>[{kind}]</div>}
                  {m.text && <div className={styles.text}>{m.text}</div>}
                </div>
                <div className={styles.meta}>
                  {out ? `${admin.tgBotFromAdmin}${m.admin_name ? `: ${m.admin_name}` : ""}` : admin.tgBotFromUser}
                  {" · "}
                  {fmtDate(m.sent_at)}
                  {" · "}
                  <span className={`${styles.status} ${styles[`st_${m.status}`] ?? ""}`}>
                    {admin.tgBotStatus[m.status] ?? m.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
