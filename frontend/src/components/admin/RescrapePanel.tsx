import { useCallback, useEffect, useState } from "react";
import { getRescrapeStatus, runRescrape, type RescrapeStatus } from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./RescrapePanel.module.css";

interface Props {
  t: AdminStrings;
  // Tekshiruv tugab, hujjatlar o'zgargan bo'lsa — ro'yxatni yangilash
  onFinished: () => void;
}

// Ishlayotganda holatni shu oraliqda so'raymiz
const POLL_MS = 5000;

function fmtDateTime(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Bilim bazasi ro'yxati tepasidagi qator: saytdan olingan hujjatlarni qayta
// tekshirish (haftalik avtomatik + "Hozir tekshirish") va oxirgi natija.
export default function RescrapePanel({ t: admin, onFinished }: Props) {
  const [status, setStatus] = useState<RescrapeStatus | null>(null);
  const [queued, setQueued] = useState(false);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus(await getRescrapeStatus());
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.rescrapeError);
    }
  }, [admin.rescrapeError]);

  useEffect(() => {
    void load();
  }, [load]);

  const busy = queued || !!status?.running;

  // Navbatga qo'yilgandan keyin tugaguncha holatni kuzatamiz
  useEffect(() => {
    if (!busy) return;
    const startedBefore = status?.last?.finished_at;
    const id = window.setInterval(async () => {
      try {
        const s = await getRescrapeStatus();
        setStatus(s);
        if (!s.running && s.last?.finished_at && s.last.finished_at !== startedBefore) {
          setQueued(false);
          if (s.last.changed.length > 0) onFinished();
        }
      } catch {
        /* keyingi urinishda */
      }
    }, POLL_MS);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy]);

  const start = async () => {
    try {
      await runRescrape();
      setQueued(true);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.rescrapeError);
    }
  };

  const last = status?.last;

  return (
    <div className={styles.bar}>
      <div className={styles.main}>
        <span className={styles.title}>{admin.rescrapeTitle}</span>
        <span className={styles.schedule}>
          {status && !status.enabled ? admin.rescrapeDisabled : admin.rescrapeSchedule}
        </span>
        {busy ? (
          <span className={styles.running}><span className={styles.spinner} />{admin.rescrapeRunning}</span>
        ) : last ? (
          <button type="button" className={styles.summary} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            {admin.rescrapeLast(fmtDateTime(last.finished_at), last.checked, last.changed.length, last.failed.length)}
          </button>
        ) : (
          <span className={styles.muted}>{admin.rescrapeNever}</span>
        )}
        <button type="button" className={styles.runBtn} onClick={() => void start()} disabled={busy}>
          {admin.rescrapeRun}
        </button>
      </div>
      {err && <div className={styles.err}>{err}</div>}
      {open && last && !busy && (last.changed.length > 0 || last.failed.length > 0) && (
        <div className={styles.details}>
          {last.changed.length > 0 && (
            <div>
              <div className={styles.detailHead}>{admin.rescrapeChanged}</div>
              <ul>{last.changed.map((t) => <li key={t}>{t}</li>)}</ul>
            </div>
          )}
          {last.failed.length > 0 && (
            <div>
              <div className={styles.detailHead}>{admin.rescrapeFailed}</div>
              <ul>
                {last.failed.map((f) => (
                  <li key={f.title}>
                    {f.title} <span className={styles.muted}>({f.error === "empty" ? admin.rescrapeEmpty : f.error})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
