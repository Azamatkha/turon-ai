import { useCallback, useEffect, useState } from "react";
import {
  generateEvalCases,
  getEvalRun,
  getEvalStatus,
  listEvalRuns,
  startEvalRun,
  type EvalResult,
  type EvalRun,
  type EvalRunDetail,
  type EvalStatus,
} from "../../services/evalService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./EvalView.module.css";

interface EvalViewProps {
  mounted: boolean;
  t: AdminStrings;
}

// Jarayon ketayotganda (savol tuzish yoki o'lchov) holat shu oraliqda yangilanadi
const POLL_MS = 8000;

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(1)}%`;
}

// Oldingi o'lchovga nisbatan farq: ▲ yaxshilandi, ▼ yomonlashdi
function Delta({ now, prev }: { now: number | null; prev: number | null }) {
  if (now == null || prev == null) return null;
  const d = Math.round((now - prev) * 10) / 10;
  if (d === 0) return <span className={styles.deltaFlat}>±0</span>;
  return (
    <span className={d > 0 ? styles.deltaUp : styles.deltaDown}>
      {d > 0 ? "▲" : "▼"} {Math.abs(d).toFixed(1)}
    </span>
  );
}

function Progress({ done, total }: { done: number; total: number }) {
  const w = total > 0 ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div className={styles.bar}>
      <div className={styles.barFill} style={{ width: `${w}%` }} />
    </div>
  );
}

function ResultItem({ r, admin }: { r: EvalResult; admin: AdminStrings }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.result}>
      <button type="button" className={styles.resultHead} onClick={() => setOpen((o) => !o)}>
        <span className={r.passed ? styles.badgeOk : styles.badgeBad}>
          {r.passed ? admin.evalPassed : admin.evalFailures[r.failure] ?? r.failure}
        </span>
        <span className={styles.styleTag}>{admin.evalStyles[r.style] ?? r.style}</span>
        <span className={styles.resultQ}>{r.question}</span>
        <span className={styles.docTitle}>{r.doc_title}</span>
      </button>
      {open && (
        <div className={styles.resultBody}>
          {r.note && (
            <div className={styles.field}>
              <div className={styles.label}>{admin.evalJudge}</div>
              <div className={styles.note}>{r.note}</div>
            </div>
          )}
          {r.expected.length > 0 && (
            <div className={styles.field}>
              <div className={styles.label}>{admin.evalExpected}</div>
              <div className={styles.chips}>
                {r.expected.map((f) => (
                  <span key={f} className={styles.chip}>{f}</span>
                ))}
              </div>
            </div>
          )}
          <div className={styles.field}>
            <div className={styles.label}>{admin.evalAnswer}</div>
            <div className={styles.answer}>{r.answer || "—"}</div>
          </div>
          <div className={styles.field}>
            <div className={styles.label}>{admin.evalSources}</div>
            <div className={styles.chips}>
              {r.source_titles.map((s) => (
                <span key={s} className={s === r.doc_title ? styles.chipHit : styles.chip}>{s}</span>
              ))}
              {!r.source_hit && <span className={styles.miss}>{admin.evalSourceMiss}</span>}
            </div>
          </div>
          <div className={styles.meta}>
            {(r.latency_ms / 1000).toFixed(1)} s · {r.intent ?? "—"} · {r.pipeline_verdict ?? "—"}
          </div>
        </div>
      )}
    </div>
  );
}

function RunDetail({
  run,
  failedOnly,
  setFailedOnly,
  onBack,
  admin,
}: {
  run: EvalRunDetail;
  failedOnly: boolean;
  setFailedOnly: (v: boolean) => void;
  onBack: () => void;
  admin: AdminStrings;
}) {
  const s = run.summary;
  const failures = s ? Object.entries(s.by_failure).sort((a, b) => b[1] - a[1]) : [];
  return (
    <div>
      <div className={styles.toolbar}>
        <button type="button" className={styles.btn} onClick={onBack}>
          ← {admin.evalBack}
        </button>
        <span className={styles.muted}>{fmtDate(run.created_at)}</span>
      </div>

      <div className={styles.stats}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>{admin.evalScore}</div>
          <div className={styles.statValue}>
            {pct(run.pass_rate)} <Delta now={run.pass_rate} prev={run.prev_pass_rate} />
          </div>
          <div className={styles.muted}>
            {run.passed} / {run.status === "done" ? run.total : run.done}
          </div>
        </div>
        {s && (
          <>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>{admin.evalByFailure}</div>
              {failures.length === 0 && <div className={styles.muted}>—</div>}
              {failures.map(([k, n]) => (
                <div key={k} className={styles.kv}>
                  <span>{admin.evalFailures[k] ?? k}</span>
                  <b>{n}</b>
                </div>
              ))}
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>{admin.evalByStyle}</div>
              {Object.entries(s.by_style).map(([k, v]) => (
                <div key={k} className={styles.kv}>
                  <span>{admin.evalStyles[k] ?? k}</span>
                  <b>{v.total ? Math.round((100 * v.passed) / v.total) : 0}%</b>
                </div>
              ))}
            </div>
            <div className={styles.statCard}>
              <div className={styles.kvNote}>{admin.evalVerifierMissed(s.verifier_missed)}</div>
              <div className={styles.kvNote}>{admin.evalAvgLatency((s.avg_latency_ms / 1000).toFixed(1))}</div>
            </div>
          </>
        )}
      </div>

      {run.status === "failed" && run.error && (
        <div className={styles.error}>
          {admin.evalRunError}: {run.error}
        </div>
      )}

      <div className={styles.toolbar}>
        <button
          type="button"
          className={failedOnly ? styles.tabActive : styles.tab}
          onClick={() => setFailedOnly(true)}
        >
          {admin.evalFailedOnly}
        </button>
        <button
          type="button"
          className={failedOnly ? styles.tab : styles.tabActive}
          onClick={() => setFailedOnly(false)}
        >
          {admin.evalShowAll}
        </button>
        <span className={styles.total}>{run.results.length}</span>
      </div>

      <div className={styles.card}>
        {run.results.length === 0 && <div className={styles.empty}>{admin.evalResultsEmpty}</div>}
        {run.results.map((r) => (
          <ResultItem key={r.id} r={r} admin={admin} />
        ))}
      </div>
    </div>
  );
}

// Javob sifati sinov stendi: bazadagi hujjatlardan tuzilgan savollar botdan
// o'tkaziladi va asl hujjat bilan solishtiriladi. Har o'zgarishdan keyin
// o'tish foizi oldingi o'lchov bilan solishtirib ko'rsatiladi.
export default function EvalView({ mounted, t: admin }: EvalViewProps) {
  const [status, setStatus] = useState<EvalStatus | null>(null);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [maxDocs, setMaxDocs] = useState(30);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [failedOnly, setFailedOnly] = useState(true);

  const load = useCallback(async () => {
    try {
      const [st, list] = await Promise.all([getEvalStatus(), listEvalRuns()]);
      setStatus(st);
      setRuns(list);
      setErr(null);
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.evalLoadError);
    }
  }, [admin.evalLoadError]);

  const loadDetail = useCallback(async () => {
    if (!selected) return;
    try {
      setDetail(await getEvalRun(selected, failedOnly));
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.evalLoadError);
    }
  }, [selected, failedOnly, admin.evalLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setDetail(null);
    void loadDetail();
  }, [loadDetail]);

  const active = Boolean(status?.generating || status?.active_run);
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => {
      void load();
      if (selected && status?.active_run?.id === selected) void loadDetail();
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [active, load, loadDetail, selected, status?.active_run?.id]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      setErr(null);
      await load();
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.evalLoadError);
    } finally {
      setBusy(false);
    }
  };

  const generate = () => {
    if (status && status.cases > 0 && !window.confirm(admin.evalRegenerateConfirm)) return;
    void act(() => generateEvalCases(maxDocs));
  };

  const run = status?.active_run ?? null;
  const cls = mounted ? `${styles.wrap} ${styles.in}` : styles.wrap;

  if (selected) {
    return (
      <div className={cls}>
        {err && <div className={styles.error}>{err}</div>}
        {detail ? (
          <RunDetail
            run={detail}
            failedOnly={failedOnly}
            setFailedOnly={setFailedOnly}
            onBack={() => setSelected(null)}
            admin={admin}
          />
        ) : (
          <div className={styles.empty}>…</div>
        )}
      </div>
    );
  }

  return (
    <div className={cls}>
      <p className={styles.hint}>{admin.evalHint}</p>
      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.panel}>
        <div className={styles.panelInfo}>
          <div className={styles.panelTitle}>
            {status && status.cases > 0 ? admin.evalCasesCount(status.cases) : admin.evalCasesNone}
          </div>
          {status && status.cases > 0 && (
            <div className={styles.chips}>
              {Object.entries(status.by_style).map(([k, n]) => (
                <span key={k} className={styles.chip}>
                  {admin.evalStyles[k] ?? k}: {n}
                </span>
              ))}
            </div>
          )}
          {status?.generating && <div className={styles.live}>{admin.evalGenerating}</div>}
          {run && (
            <div className={styles.live}>
              {admin.evalRunProgress(run.done, run.total)}
              <Progress done={run.done} total={run.total} />
            </div>
          )}
        </div>
        <div className={styles.panelActions}>
          <label className={styles.docsLabel}>
            {admin.evalDocsLabel}
            <input
              type="number"
              min={1}
              max={300}
              value={maxDocs}
              onChange={(e) => setMaxDocs(Math.max(1, Math.min(300, Number(e.target.value) || 1)))}
              className={styles.docsInput}
            />
          </label>
          <button type="button" className={styles.btn} onClick={generate} disabled={busy || active}>
            {admin.evalGenerateBtn}
          </button>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={() => void act(startEvalRun)}
            disabled={busy || active || !status?.cases}
          >
            {admin.evalRunBtn}
          </button>
        </div>
      </div>

      <div className={styles.sectionTitle}>{admin.evalRunsTitle}</div>
      <div className={styles.card}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span>{admin.evalColDate}</span>
          <span>{admin.evalColStatus}</span>
          <span>{admin.evalColProgress}</span>
          <span>{admin.evalColScore}</span>
        </div>
        {runs.length === 0 && <div className={styles.empty}>{admin.evalRunsEmpty}</div>}
        {runs.map((r) => (
          <button key={r.id} type="button" className={`${styles.row} ${styles.rowBtn}`} onClick={() => setSelected(r.id)}>
            <span className={styles.muted}>{fmtDate(r.created_at)}</span>
            <span className={styles[`st_${r.status}`]}>{admin.evalStatus[r.status] ?? r.status}</span>
            <span>
              {r.done} / {r.total}
            </span>
            <span className={styles.score}>
              {pct(r.pass_rate)} <Delta now={r.pass_rate} prev={r.prev_pass_rate} />
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
