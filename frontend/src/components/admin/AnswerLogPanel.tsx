import { forwardRef, useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
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

type FilterKey = "all" | "rejected" | "failed" | "no_info";

const PAGE_SIZE = 30;

function filterQuery(f: FilterKey): Pick<AnswerLogQuery, "verdict" | "outcome"> {
  if (f === "rejected") return { verdict: "rejected" };
  if (f === "failed") return { verdict: "failed" };
  if (f === "no_info") return { outcome: "no_info" };
  return {};
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Savol + bot javobi jurnali: admin bot to'g'ri javob berayaptimi, o'z ko'zi
// bilan ko'radi. Qatorni bossa — javob to'liq ochiladi.
const AnswerLogPanel = forwardRef<HTMLElement, AnswerLogPanelProps>(function AnswerLogPanel(
  { days, t: admin, search, onSearchChange, reloadKey },
  ref,
) {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [items, setItems] = useState<AnswerLogItem[]>([]);
  const [meta, setMeta] = useState<AnswerLogPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  // Qidiruv har harfda emas, yozib bo'lgach ketadi
  const [query, setQuery] = useState(search);

  useEffect(() => {
    const id = window.setTimeout(() => setQuery(search), 350);
    return () => window.clearTimeout(id);
  }, [search]);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const res = await getAnswerLog({ days, search: query, page: p, size: PAGE_SIZE, ...filterQuery(filter) });
        setMeta(res);
        setItems((prev) => (p === 1 ? res.items : [...prev, ...res.items]));
        setPage(p);
        setErr(null);
      } catch (e) {
        setErr((e instanceof Error && e.message) || admin.questionsLoadError);
      } finally {
        setLoading(false);
      }
    },
    [days, query, filter, admin.questionsLoadError],
  );

  useEffect(() => {
    setOpen(null);
    void load(1);
  }, [load, reloadKey]);

  const v = meta?.verdicts ?? {};
  const hasMore = !!meta && items.length < meta.total;

  return (
    <section ref={ref} className={styles.panel}>
      <header className={styles.head}>
        <div>
          <div className={styles.title}>{admin.answersTitle}</div>
          <div className={styles.hint}>{admin.answersHint}</div>
          {meta && (
            <div className={styles.summary}>
              {admin.answersVerdictSummary(v.ok ?? 0, v.fixed ?? 0, v.failed ?? 0)}
            </div>
          )}
        </div>
        <div className={styles.controls}>
          <input
            className={styles.search}
            type="search"
            value={search}
            placeholder={admin.answersSearchPh}
            onChange={(e) => onSearchChange(e.target.value)}
          />
          <FilterSelect
            value={filter}
            onChange={(val) => setFilter(val as FilterKey)}
            options={[
              { value: "all", label: admin.answersFilterAll },
              { value: "rejected", label: admin.answersFilterRejected },
              { value: "failed", label: admin.answersFilterFailed },
              { value: "no_info", label: admin.answersFilterNoInfo },
            ]}
          />
        </div>
      </header>

      {err && <div className={styles.error}>{err}</div>}

      {!loading && items.length === 0 && !err ? (
        <div className={styles.empty}>{admin.answersEmpty}</div>
      ) : (
        <ul className={styles.list}>
          {items.map((it) => {
            const isOpen = open === it.id;
            const verdict = it.verdict ?? null;
            return (
              <li key={it.id} className={styles.row}>
                <button
                  type="button"
                  className={styles.rowHead}
                  aria-expanded={isOpen}
                  onClick={() => setOpen(isOpen ? null : it.id)}
                >
                  <span className={styles.q}>{it.question}</span>
                  <span className={styles.meta}>
                    {verdict && (
                      <span className={`${styles.badge} ${styles[`v_${verdict}`] ?? ""}`}>
                        {admin.answersVerdict[verdict]}
                      </span>
                    )}
                    <span className={styles.sub}>
                      {it.username ?? "—"} · {fmtDateTime(it.created_at)} · {(it.duration_ms / 1000).toFixed(1)} s
                    </span>
                  </span>
                  <span className={`${styles.chev} ${isOpen ? styles.chevOpen : ""}`} aria-hidden>
                    ›
                  </span>
                </button>
                {!isOpen && <div className={styles.preview}>{it.answer || admin.answersMissing}</div>}
                {isOpen && (
                  <div className={styles.body}>
                    <div className={styles.label}>{admin.answersQuestion}</div>
                    <div className={styles.text}>{it.question}</div>
                    <div className={styles.label}>{admin.answersAnswer}</div>
                    <div className={styles.text}>{it.answer || admin.answersMissing}</div>
                    {it.verdict_note && (
                      <>
                        <div className={styles.label}>{admin.answersNote}</div>
                        <div className={`${styles.text} ${styles.note}`}>{it.verdict_note}</div>
                      </>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {hasMore && (
        <div className={styles.footer}>
          <button type="button" className={styles.moreBtn} disabled={loading} onClick={() => void load(page + 1)}>
            {admin.answersMore}
          </button>
        </div>
      )}
    </section>
  );
});

export default AnswerLogPanel;
