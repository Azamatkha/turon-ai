import { useCallback, useEffect, useState } from "react";
import { getBackups, runQdrantBackup, type BackupKind, type BackupOverview } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./BackupsView.module.css";

interface BackupsViewProps {
  mounted: boolean;
  t: AdminStrings;
}

// Nusxa shundan eski bo'lsa — ogohlantirish (kunlik nusxa o'tkazib yuborilgan)
const STALE_MS = 36 * 60 * 60 * 1000;

function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

export default function BackupsView({ mounted, t: admin }: BackupsViewProps) {
  const [data, setData] = useState<BackupOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [queued, setQueued] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getBackups());
      setErr(null);
    } catch (e) {
      setData(null);
      setErr((e instanceof Error && e.message) || admin.backupLoadError);
    } finally {
      setLoading(false);
    }
  }, [admin.backupLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const runNow = async () => {
    try {
      await runQdrantBackup();
      setQueued(true);
      // Snapshot bir necha soniya oladi — keyin ro'yxatni yangilaymiz
      window.setTimeout(() => {
        setQueued(false);
        void load();
      }, 8000);
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.backupLoadError);
    }
  };

  const kindLabel: Record<BackupKind, string> = {
    postgres: admin.backupKindPostgres,
    qdrant: admin.backupKindQdrant,
  };

  // Holat: muvaffaqiyatsiz / eskirgan / hali yo'q / yaxshi
  const health = (s: BackupOverview["statuses"][number]) => {
    if (s.last_result === "fail") return { cls: styles.bad, text: admin.backupStateFailed };
    if (!s.latest_at) return { cls: styles.warn, text: admin.backupStateNone };
    if (Date.now() - new Date(s.latest_at).getTime() > STALE_MS) return { cls: styles.warn, text: admin.backupStateStale };
    return { cls: styles.good, text: admin.backupStateOk };
  };

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <p className={styles.hint}>{admin.backupHint(data?.keep_days ?? 14)}</p>
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
        <button type="button" className={styles.runBtn} onClick={() => void runNow()} disabled={queued}>
          {queued ? admin.backupQueued : admin.backupRunQdrant}
        </button>
      </div>

      {err && <div className={styles.error}>{err}</div>}
      {data && !data.available && <div className={styles.warnBox}>{admin.backupNotMounted}</div>}

      {data && (
        <div className={styles.cards}>
          {data.statuses.map((s) => {
            const h = health(s);
            return (
              <section key={s.kind} className={styles.card}>
                <header className={styles.cardHead}>
                  <span className={styles.cardTitle}>{kindLabel[s.kind]}</span>
                  <span className={`${styles.state} ${h.cls}`}>{h.text}</span>
                </header>
                <dl className={styles.facts}>
                  <dt>{admin.backupLatest}</dt>
                  <dd>{fmtDate(s.latest_at)}</dd>
                  <dt>{admin.backupLastRun}</dt>
                  <dd>{fmtDate(s.last_run_at)}</dd>
                  <dt>{admin.backupCount}</dt>
                  <dd>{s.count} · {fmtSize(s.total_size)}</dd>
                </dl>
              </section>
            );
          })}
        </div>
      )}

      <div className={styles.table}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span>{admin.backupColFile}</span>
          <span>{admin.backupColKind}</span>
          <span>{admin.backupColSize}</span>
          <span>{admin.reportColDate}</span>
        </div>
        {!loading && (data?.files.length ?? 0) === 0 && <div className={styles.empty}>{admin.backupEmpty}</div>}
        {data?.files.map((f) => (
          <div key={f.kind + f.name} className={styles.row}>
            <span className={styles.fileName} title={f.name}>{f.name}</span>
            <span>{kindLabel[f.kind]}</span>
            <span className={styles.num}>{fmtSize(f.size)}</span>
            <span className={styles.num}>{fmtDate(f.created_at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
