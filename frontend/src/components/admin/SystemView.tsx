import { useCallback, useEffect, useState } from "react";
import StatCard, { type StatDef } from "./StatCard";
import { getSystemStatus, type SystemStatus } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./SystemView.module.css";

interface SystemViewProps {
  mounted: boolean;
  t: AdminStrings;
}

// Sahifa ochiq turganda holat o'zi yangilanib tursin
const REFRESH_MS = 30_000;

const COMPONENT_NAMES: Record<string, string> = {
  postgres: "PostgreSQL",
  redis: "Redis",
  qdrant: "Qdrant",
  ollama: "Ollama (LLM)",
  rabbitmq: "RabbitMQ",
  celery: "Celery worker",
};

const sec = (ms: number) => (ms / 1000).toFixed(ms < 10_000 ? 1 : 0) + " s";

const icon = (path: React.ReactNode) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{path}</svg>
);

export default function SystemView({ mounted, t: admin }: SystemViewProps) {
  const [data, setData] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getSystemStatus());
      setErr(null);
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.systemLoadError);
    } finally {
      setLoading(false);
    }
  }, [admin.systemLoadError]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => {
      if (!document.hidden) void load();
    }, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [load]);

  const llm = data?.llm;
  const errPct = llm && llm.questions > 0 ? Math.round((llm.errors / llm.questions) * 100) : 0;
  const stats: StatDef[] = [
    {
      icon: icon(<><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></>),
      value: llm ? llm.questions.toLocaleString() : "—",
      label: admin.systemStatQuestions,
      trend: "",
      tint: "var(--adm-accent)",
      tintBg: "var(--adm-accent-bg)",
    },
    {
      icon: icon(<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>),
      value: llm ? sec(llm.p50_ms) : "—",
      label: admin.systemStatP50,
      trend: "",
      tint: "var(--adm-info)",
      tintBg: "var(--adm-info-bg)",
    },
    {
      icon: icon(<><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></>),
      value: llm ? sec(llm.p95_ms) : "—",
      label: admin.systemStatP95,
      trend: llm && llm.max_ms > 0 ? `max ${sec(llm.max_ms)}` : "",
      tint: "var(--adm-accent)",
      tintBg: "var(--adm-accent-bg)",
    },
    {
      icon: icon(<><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>),
      value: llm ? llm.errors.toLocaleString() : "—",
      label: admin.systemStatErrors,
      trend: llm && llm.questions > 0 ? `${errPct}%` : "",
      tint: "var(--adm-danger)",
      tintBg: "var(--adm-danger-bg)",
    },
  ];

  // Kesh: keshdan berilgan javoblar ulushi (keshlanadigan savollar ichida)
  const cacheTotal = llm ? llm.cache_hits_today + llm.cache_misses_today : 0;
  const cachePct = llm && cacheTotal > 0 ? Math.round((llm.cache_hits_today / cacheTotal) * 100) : 0;
  stats.push({
    icon: icon(<><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></>),
    value: llm ? llm.cache_hits_today.toLocaleString() : "—",
    label: admin.systemStatCache,
    trend: cacheTotal > 0 ? `${cachePct}%` : "",
    tint: "var(--adm-success)",
    tintBg: "var(--adm-success-bg)",
  });

  const hourly = llm?.hourly ?? [];
  const maxQ = Math.max(1, ...hourly.map((h) => h.questions));

  const banner =
    data?.status === "down"
      ? { cls: styles.bannerDown, text: admin.systemDown }
      : data?.status === "degraded"
        ? { cls: styles.bannerWarn, text: admin.systemDegraded }
        : data
          ? { cls: styles.bannerOk, text: admin.systemOk }
          : null;

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        {banner && (
          <div className={`${styles.banner} ${banner.cls}`} role="status">
            <span className={styles.dot} />
            {banner.text}
          </div>
        )}
        {data && <span className={styles.checked}>{admin.systemCheckedAt(new Date(data.checked_at).toLocaleTimeString())}</span>}
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.components}>
        {(data?.components ?? []).map((c) => (
          <div key={c.name} className={`${styles.comp} ${c.ok ? "" : styles.compBad}`}>
            <div className={styles.compHead}>
              <span className={`${styles.compDot} ${c.ok ? styles.dotOk : c.critical ? styles.dotBad : styles.dotWarn}`} />
              <span className={styles.compName}>{COMPONENT_NAMES[c.name] ?? c.name}</span>
              <span className={styles.compMs}>{c.latency_ms} ms</span>
            </div>
            <div className={styles.compDetail}>
              {c.ok ? c.detail || admin.systemCompOk : `${admin.systemCompFail}${c.detail ? `: ${c.detail}` : ""}`}
            </div>
            {!c.critical && <div className={styles.compNote}>{admin.systemNonCritical}</div>}
          </div>
        ))}
      </div>

      <div className={styles.sectionTitle}>{admin.systemLlmTitle}</div>
      <div className={styles.statGrid}>
        {stats.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <section className={styles.chart} aria-label={admin.systemChartTitle}>
        <header className={styles.chartHead}>
          <span className={styles.chartTitle}>{admin.systemChartTitle}</span>
          <span className={styles.legend}>
            <span className={`${styles.legendSwatch} ${styles.swQ}`} /> {admin.systemStatQuestions}
            <span className={`${styles.legendSwatch} ${styles.swE}`} /> {admin.systemStatErrors}
          </span>
        </header>
        <div className={styles.bars}>
          {hourly.map((h) => {
            const d = new Date(h.hour);
            const label = String(d.getHours()).padStart(2, "0");
            const tip = `${label}:00 — ${h.questions} · ${admin.systemStatErrors.toLowerCase()}: ${h.errors} · ${sec(h.avg_ms)}`;
            return (
              <div key={h.hour} className={styles.barCol} title={tip}>
                <div className={styles.barTrack}>
                  <div className={styles.barQ} style={{ height: `${(h.questions / maxQ) * 100}%` }}>
                    {h.errors > 0 && (
                      <div className={styles.barE} style={{ height: `${(h.errors / Math.max(1, h.questions)) * 100}%` }} />
                    )}
                  </div>
                </div>
                <span className={styles.barLabel}>{label}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
