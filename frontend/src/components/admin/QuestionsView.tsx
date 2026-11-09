import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import StatCard, { type StatDef } from "./StatCard";
import { getQuestionAnalytics, type QuestionAnalytics, type QuestionStatItem } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./QuestionsView.module.css";

interface QuestionsViewProps {
  mounted: boolean;
  t: AdminStrings;
}

const PERIODS = [7, 30, 90] as const;

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

const icon = (path: React.ReactNode) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{path}</svg>
);

// Savollar tahlili: eng ko'p so'ralgan va bazada javob topilmagan savollar.
// Javobsizlar ro'yxati — bilim bazasiga nima qo'shish kerakligining ro'yxati.
export default function QuestionsView({ mounted, t: admin }: QuestionsViewProps) {
  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<QuestionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getQuestionAnalytics(days, 20));
      setErr(null);
    } catch (e) {
      setData(null);
      setErr((e instanceof Error && e.message) || admin.questionsLoadError);
    } finally {
      setLoading(false);
    }
  }, [days, admin.questionsLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const sm = data?.summary;
  const fmt = (n: number) => n.toLocaleString();
  const noInfoPct = sm && sm.total > 0 ? Math.round((sm.no_info / sm.total) * 100) : 0;

  const stats: StatDef[] = [
    {
      icon: icon(<><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></>),
      value: sm ? fmt(sm.total) : "—",
      label: admin.questionsStatTotal,
      trend: "",
      tint: "var(--adm-accent)",
      tintBg: "var(--adm-accent-bg)",
    },
    {
      icon: icon(<><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" /></>),
      value: sm ? fmt(sm.no_info) : "—",
      label: admin.questionsStatNoInfo,
      trend: sm && sm.total > 0 ? `${noInfoPct}%` : "",
      tint: "var(--adm-danger)",
      tintBg: "var(--adm-danger-bg)",
    },
    {
      icon: icon(<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>),
      value: sm ? (sm.avg_duration_ms / 1000).toFixed(1) + " s" : "—",
      label: admin.questionsStatAvgTime,
      trend: "",
      tint: "var(--adm-info)",
      tintBg: "var(--adm-info-bg)",
    },
    {
      icon: icon(<><circle cx="12" cy="12" r="9" /><path d="M14.8 9A2 2 0 0 0 13 8h-2a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-1.8-1" /><path d="M12 6v2m0 8v2" /></>),
      value: sm ? fmt(sm.total_tokens) : "—",
      label: admin.questionsStatTokens,
      trend: sm && sm.errors > 0 ? admin.questionsErrors(sm.errors) : "",
      tint: "var(--adm-success)",
      tintBg: "var(--adm-success-bg)",
    },
  ];

  const list = (title: string, hint: string, rows: QuestionStatItem[], danger: boolean) => (
    <section className={styles.panel}>
      <header className={styles.panelHead}>
        <div className={styles.panelTitle}>{title}</div>
        <div className={styles.panelHint}>{hint}</div>
      </header>
      {!loading && rows.length === 0 ? (
        <div className={styles.empty}>{admin.questionsEmpty}</div>
      ) : (
        <ol className={styles.list}>
          {rows.map((r, i) => (
            <li key={r.question + i} className={styles.item}>
              <span className={styles.rank}>{i + 1}</span>
              <span className={styles.q} title={r.question}>{r.question}</span>
              <span className={styles.meta}>
                <span className={`${styles.count} ${danger ? styles.countDanger : ""}`}>×{r.count}</span>
                <span className={styles.sub}>
                  {admin.questionsUsers(r.users)} · {fmtDate(r.last_asked)}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <FilterSelect
          value={String(days)}
          onChange={(v) => setDays(Number(v))}
          options={PERIODS.map((p) => ({ value: String(p), label: admin.questionsPeriod(p) }))}
        />
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.statGrid}>
        {stats.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.columns}>
        {list(admin.questionsUnansweredTitle, admin.questionsUnansweredHint, data?.unanswered ?? [], true)}
        {list(admin.questionsTopTitle, admin.questionsTopHint, data?.top ?? [], false)}
      </div>
    </div>
  );
}
