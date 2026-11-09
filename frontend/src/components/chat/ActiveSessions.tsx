import { useCallback, useEffect, useState } from "react";
import {
  listActiveSessions,
  revokeOtherSessions,
  revokeSession,
  type ActiveSession,
} from "../../services/authService";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ActiveSessions.module.css";

interface Props {
  S: ChatStaticStrings;
  isDark: boolean;
}

function fmtDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Telefon yoki kompyuter belgisi — qurilma nomiga qarab
function DeviceIcon({ device }: { device: string }) {
  const mobile = /android|ios|app/i.test(device);
  return mobile ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="6" y="2" width="12" height="20" rx="2.5" /><line x1="11" y1="18" x2="13" y2="18" /></svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="13" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
  );
}

// Profil oynasidagi "Faol seanslar": qaysi qurilmalardan kirilgan, birini
// yoki joriydan boshqa hammasini yopish. Yopilgan qurilma keyingi so'rovda
// login sahifasiga qaytadi.
export default function ActiveSessions({ S, isDark }: Props) {
  const [items, setItems] = useState<ActiveSession[] | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  // "Boshqalardan chiqish" — tasodifiy bosilmasin, ikki bosqichli
  const [confirmOthers, setConfirmOthers] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await listActiveSessions());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const others = (items ?? []).filter((s) => !s.current);

  const closeOne = async (id: string) => {
    setBusy(id);
    try {
      await revokeSession(id);
      setItems((xs) => (xs ?? []).filter((s) => s.session_id !== id));
    } catch {
      setError(true);
    } finally {
      setBusy(null);
    }
  };

  const closeOthers = async () => {
    setBusy("others");
    try {
      const n = await revokeOtherSessions();
      setItems((xs) => (xs ?? []).filter((s) => s.current));
      setNotice(S.sessionsRevokedOthers.replace("{n}", String(n)));
    } catch {
      setError(true);
    } finally {
      setBusy(null);
      setConfirmOthers(false);
    }
  };

  return (
    <section className={`${styles.wrap} ${isDark ? styles.dark : ""}`} aria-busy={items === null}>
      <h2 className={styles.title}>{S.sessionsTitle}</h2>
      <p className={styles.hint}>{S.sessionsHint}</p>

      {error && <div className={styles.error} role="alert">{S.sessionsLoadError}</div>}
      {notice && <div className={styles.notice} role="status">{notice}</div>}

      <ul className={styles.list}>
        {items === null && !error && <li className={styles.loading}>…</li>}
        {items?.map((s) => (
          <li key={s.session_id} className={styles.item}>
            <span className={styles.icon}><DeviceIcon device={s.device} /></span>
            <span className={styles.body}>
              <span className={styles.device}>
                {s.device || S.sessionsUnknownDevice}
                {s.current && <span className={styles.current}>{S.sessionsCurrent}</span>}
              </span>
              <span className={styles.meta}>
                {s.ip || "—"} · {S.sessionsLastActive}: {fmtDateTime(s.last_seen_at)}
              </span>
            </span>
            {!s.current && (
              <button
                type="button"
                className={styles.revokeBtn}
                onClick={() => void closeOne(s.session_id)}
                disabled={busy !== null}
                title={s.user_agent || undefined}
              >
                {S.sessionsRevoke}
              </button>
            )}
          </li>
        ))}
      </ul>

      {others.length > 0 && (
        <div className={styles.footer}>
          {confirmOthers ? (
            <>
              <span className={styles.confirmText}>{S.sessionsRevokeOthersConfirm}</span>
              <button type="button" className={styles.dangerBtn} onClick={() => void closeOthers()} disabled={busy !== null}>
                {S.sessionsRevokeOthersYes}
              </button>
              <button type="button" className={styles.ghostBtn} onClick={() => setConfirmOthers(false)}>
                {S.sessionsCancel}
              </button>
            </>
          ) : (
            <button type="button" className={styles.dangerBtn} onClick={() => setConfirmOthers(true)} disabled={busy !== null}>
              {S.sessionsRevokeOthers}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
