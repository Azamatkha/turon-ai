import { forwardRef, useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import FilterSelect from "./FilterSelect";
import MessageContent from "../chat/MessageContent";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { getAnswerLog, type AnswerLogItem, type AnswerLogPage, type AnswerLogQuery } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./AnswerLogPanel.module.css";

interface AnswerLogPanelProps {
  days: number;
  t: AdminStrings;
  search: string;
  onSearchChange: (v: string) => void;
  // Tashqi "Yangilash" bosilganda o'zgaradi — ro'yxat qayta yuklanadi
  reloadKey: number;
}

type VerdictKey = "all" | "rejected" | "failed" | "ok";
type OutcomeKey = "all" | keyof AdminStrings["answersOutcome"];

const OUTCOMES: Exclude<OutcomeKey, "all">[] = ["answered", "no_info", "web", "flagged", "blocked", "error"];
const PAGE_SIZE = 40;

function buildQuery(v: VerdictKey, o: OutcomeKey): Pick<AnswerLogQuery, "verdict" | "outcome"> {
  return {
    verdict: v === "all" ? undefined : v,
    outcome: o === "all" ? undefined : o,
  };
}

const pad = (n: number) => String(n).padStart(2, "0");

function fmtShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fmtFull(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function userLabel(it: AnswerLogItem): string {
  return it.full_name || it.username || "—";
}

// Savol + bot javobi jurnali — admin bot to'g'ri javob berayaptimi, o'z ko'zi
// bilan tekshiradi. Keng ekranda: chapda savollar ro'yxati, o'ngda tanlangan
// savolning to'liq javobi va tafsilotlari. Tor ekranda javob qator ostida ochiladi.
const AnswerLogPanel = forwardRef<HTMLElement, AnswerLogPanelProps>(function AnswerLogPanel(
  { days, t: admin, search, onSearchChange, reloadKey },
  ref,
) {
  const [verdict, setVerdict] = useState<VerdictKey>("all");
  const [outcome, setOutcome] = useState<OutcomeKey>("all");
  const [items, setItems] = useState<AnswerLogItem[]>([]);
  const [meta, setMeta] = useState<AnswerLogPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  // Qidiruv har harfda emas, yozib bo'lgach ketadi
  const [query, setQuery] = useState(search);
  const wide = useMediaQuery("(min-width: 1100px)");
  const wideRef = useRef(wide);
  wideRef.current = wide;
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const id = window.setTimeout(() => setQuery(search), 350);
    return () => window.clearTimeout(id);
  }, [search]);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const res = await getAnswerLog({ days, search: query, page: p, size: PAGE_SIZE, ...buildQuery(verdict, outcome) });
        setMeta(res);
        setItems((prev) => (p === 1 ? res.items : [...prev, ...res.items]));
        setPage(p);
        setErr(null);
        // Keng ekranda birinchi savol darhol ochiq turadi; tor ekranda hech biri
        if (p === 1) setSelected(wideRef.current ? (res.items[0]?.id ?? null) : null);
      } catch (e) {
        setErr((e instanceof Error && e.message) || admin.questionsLoadError);
      } finally {
        setLoading(false);
      }
    },
    [days, query, verdict, outcome, admin.questionsLoadError],
  );

  useEffect(() => {
    void load(1);
  }, [load, reloadKey]);

  // Tanlangan qator ko'rinib tursin (klaviatura bilan yurganda)
  useEffect(() => {
    if (!selected) return;
    listRef.current
      ?.querySelector<HTMLElement>(`[data-id="${selected}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  // ↑/↓ — oldingi/keyingi savol (fokus ham o'sha qatorga o'tadi)
  const onRowKey = (e: KeyboardEvent<HTMLButtonElement>, idx: number) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const next = e.key === "ArrowDown" ? Math.min(items.length - 1, idx + 1) : Math.max(0, idx - 1);
    const it = items[next];
    if (!it) return;
    setSelected(it.id);
    listRef.current?.querySelector<HTMLButtonElement>(`[data-id="${it.id}"] button`)?.focus();
  };

  const v = meta?.verdicts ?? {};
  const hasMore = !!meta && items.length < meta.total;
  const current = items.find((it) => it.id === selected) ?? null;

  const outcomeLabel = (o: string) =>
    (admin.answersOutcome as Record<string, string>)[o] ?? o;

  const detail = (it: AnswerLogItem) => (
    <div className={styles.detail}>
      <div className={styles.label}>{admin.answersQuestion}</div>
      <div className={styles.question}>{it.question}</div>

      <dl className={styles.facts}>
        <div><dt>{admin.answersUser}</dt><dd>{userLabel(it)}{it.full_name && it.username ? ` (${it.username})` : ""}</dd></div>
        <div><dt>{admin.answersTime}</dt><dd>{fmtFull(it.created_at)}</dd></div>
        <div><dt>{admin.answersDuration}</dt><dd>{(it.duration_ms / 1000).toFixed(1)} s</dd></div>
        <div><dt>{admin.answersTokens}</dt><dd>{it.completion_tokens ?? 0}</dd></div>
        <div><dt>{admin.answersIntent}</dt><dd>{it.intent || "—"}</dd></div>
        <div><dt>{admin.answersScore}</dt><dd>{it.top_score != null ? it.top_score.toFixed(3) : "—"}</dd></div>
        <div><dt>{admin.answersSources}</dt><dd>{it.sources_count ?? 0}</dd></div>
      </dl>

      <div className={styles.badges}>
        <span className={`${styles.badge} ${styles[`o_${it.outcome}`] ?? ""}`}>{outcomeLabel(it.outcome)}</span>
        {it.verdict && (
          <span className={`${styles.badge} ${styles[`v_${it.verdict}`] ?? ""}`}>{admin.answersVerdict[it.verdict]}</span>
        )}
      </div>

      <div className={styles.label}>{admin.answersAnswer}</div>
      <div className={styles.answer}>
        {it.answer ? <MessageContent text={it.answer} /> : <span className={styles.missing}>{admin.answersMissing}</span>}
      </div>

      {it.verdict_note && (
        <>
          <div className={styles.label}>{admin.answersNote}</div>
          <div className={styles.note}>{it.verdict_note}</div>
        </>
      )}

      {!!it.source_urls?.length && (
        <>
          <div className={styles.label}>{admin.answersSources}</div>
          <ul className={styles.urls}>
            {it.source_urls.map((u) => (
              <li key={u}>
                <a href={u} target="_blank" rel="noreferrer noopener">{u}</a>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );

  return (
    <section ref={ref} className={styles.panel}>
      <header className={styles.head}>
        <input
          className={styles.search}
          type="search"
          value={search}
          placeholder={admin.answersSearchPh}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <FilterSelect
          value={outcome}
          onChange={(val) => setOutcome(val as OutcomeKey)}
          options={[
            { value: "all", label: admin.answersAllOutcomes },
            ...OUTCOMES.map((o) => ({ value: o, label: admin.answersOutcome[o] })),
          ]}
        />
        <FilterSelect
          value={verdict}
          onChange={(val) => setVerdict(val as VerdictKey)}
          options={[
            { value: "all", label: admin.answersAllVerdicts },
            { value: "ok", label: admin.answersFilterOk },
            { value: "rejected", label: admin.answersFilterRejected },
            { value: "failed", label: admin.answersFilterFailed },
          ]}
        />
        <div className={styles.summary}>
          {meta && <strong>{admin.answersCount(meta.total)}</strong>}
          {meta && <span>{admin.answersVerdictSummary(v.ok ?? 0, v.fixed ?? 0, v.failed ?? 0)}</span>}
        </div>
      </header>

      {err && <div className={styles.error}>{err}</div>}

      {!loading && items.length === 0 && !err ? (
        <div className={styles.empty}>{admin.answersEmpty}</div>
      ) : (
        <div className={styles.split}>
          <div className={styles.listCol}>
            <ul ref={listRef} className={styles.list} aria-label={admin.questionsTabLog}>
              {items.map((it, idx) => {
                const active = it.id === selected;
                return (
                  <li key={it.id} data-id={it.id} className={`${styles.row} ${active ? styles.rowActive : ""}`}>
                    <button
                      type="button"
                      className={styles.rowBtn}
                      aria-current={active || undefined}
                      onClick={() => setSelected(!wide && active ? null : it.id)}
                      onKeyDown={(e) => onRowKey(e, idx)}
                    >
                      <span className={styles.rowTop}>
                        <span className={styles.time}>{fmtShort(it.created_at)}</span>
                        <span className={styles.user}>{userLabel(it)}</span>
                        <span className={styles.rowBadges}>
                          {it.outcome !== "answered" && (
                            <span className={`${styles.dot} ${styles[`o_${it.outcome}`] ?? ""}`}>{outcomeLabel(it.outcome)}</span>
                          )}
                          {it.verdict && it.verdict !== "ok" && (
                            <span className={`${styles.dot} ${styles[`v_${it.verdict}`] ?? ""}`}>{admin.answersVerdict[it.verdict]}</span>
                          )}
                        </span>
                      </span>
                      <span className={styles.q}>{it.question}</span>
                      {!active && <span className={styles.preview}>{it.answer || admin.answersMissing}</span>}
                    </button>
                    {!wide && active && detail(it)}
                  </li>
                );
              })}
            </ul>
            {hasMore && (
              <div className={styles.footer}>
                <button type="button" className={styles.moreBtn} disabled={loading} onClick={() => void load(page + 1)}>
                  {admin.answersMore}
                </button>
              </div>
            )}
          </div>

          {wide && (
            <aside className={styles.detailCol}>
              {current ? detail(current) : <div className={styles.empty}>{admin.answersSelectHint}</div>}
              <div className={styles.keysHint}>{admin.answersKeysHint}</div>
            </aside>
          )}
        </div>
      )}
    </section>
  );
});

export default AnswerLogPanel;
