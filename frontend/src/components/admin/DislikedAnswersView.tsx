import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import {
  listDislikedAnswers,
  reviewDislikedAnswer,
  type ApiDislikedAnswer,
} from "../../services/feedbackService";
import type { VoteReason } from "../../types/chat";
import type { AdminStrings } from "../../types/i18n";
import styles from "./DislikedAnswersView.module.css";

interface DislikedAnswersViewProps {
  mounted: boolean;
  t: AdminStrings;
  // Navbatdagi (ko'rib chiqilmagan) javoblar soni — yon paneldagi belgi uchun
  onCountChange?: (n: number) => void;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Bir hujjatning bir nechta bo'lagi kelishi mumkin — sarlavha bo'yicha takrorsiz
function uniqueTitles(item: ApiDislikedAnswer): string[] {
  return [...new Set((item.sources ?? []).map((s) => s.title.trim()).filter(Boolean))];
}

export default function DislikedAnswersView({ mounted, t: admin, onCountChange }: DislikedAnswersViewProps) {
  const [items, setItems] = useState<ApiDislikedAnswer[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"open" | "all">("open");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [busyId, setBusyId] = useState<string | null>(null);

  const reasonLabel: Record<VoteReason, string> = {
    wrong: admin.dislikedReasonWrong,
    outdated: admin.dislikedReasonOutdated,
    incomplete: admin.dislikedReasonIncomplete,
    other: admin.dislikedReasonOther,
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDislikedAnswers({ onlyOpen: filter === "open", size: 100 });
      setItems(data.items);
      setTotal(data.total);
      if (filter === "open") onCountChange?.(data.total);
      setErr(null);
    } catch (e) {
      setItems([]);
      setTotal(0);
      setErr((e instanceof Error && e.message) || admin.dislikedLoadError);
    } finally {
      setLoading(false);
    }
  }, [filter, admin.dislikedLoadError, onCountChange]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleExpand = (id: string) =>
    setExpanded((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const setReviewed = async (item: ApiDislikedAnswer, reviewed: boolean) => {
    setBusyId(item.id);
    try {
      await reviewDislikedAnswer(item.id, reviewed);
      if (filter === "open" && reviewed) {
        // Navbatdan chiqadi
        setItems((xs) => xs.filter((x) => x.id !== item.id));
        setTotal((n) => {
          onCountChange?.(Math.max(0, n - 1));
          return Math.max(0, n - 1);
        });
      } else {
        setItems((xs) => xs.map((x) => (x.id === item.id ? { ...x, reviewed } : x)));
      }
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.dislikedLoadError);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <p className={styles.hint}>{admin.dislikedHint}</p>
      <div className={styles.toolbar}>
        <FilterSelect
          value={filter}
          onChange={(v) => setFilter(v as "open" | "all")}
          options={[
            { value: "open", label: admin.dislikedFilterOpen },
            { value: "all", label: admin.dislikedFilterAll },
          ]}
        />
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
        <span className={styles.total}>{admin.faceLogsTotal(total)}</span>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      {!loading && items.length === 0 && !err && (
        <div className={styles.empty}>{admin.dislikedEmpty}</div>
      )}

      <div className={styles.list}>
        {items.map((item) => {
          const open = expanded.has(item.id);
          const titles = uniqueTitles(item);
          return (
            <article key={item.id} className={`${styles.card} ${item.reviewed ? styles.cardDone : ""}`}>
              <header className={styles.cardHead}>
                <span className={styles.user}>
                  {item.user_name}
                  <span className={styles.handle}>@{item.username}</span>
                </span>
                {item.reason && <span className={styles.reason}>{reasonLabel[item.reason]}</span>}
                {item.reviewed && <span className={styles.done}>{admin.dislikedReviewedBadge}</span>}
                <span className={styles.date}>{fmtDate(item.created_at)}</span>
              </header>

              <div className={styles.label}>{admin.dislikedQuestion}</div>
              <div className={styles.question}>{item.question || "—"}</div>

              <div className={styles.label}>{admin.dislikedAnswer}</div>
              <div className={`${styles.answer} ${open ? "" : styles.answerClamp}`}>{item.answer}</div>
              <button type="button" className={styles.more} onClick={() => toggleExpand(item.id)}>
                {open ? admin.dislikedCollapse : admin.dislikedExpand}
              </button>

              {item.comment && (
                <>
                  <div className={styles.label}>{admin.dislikedComment}</div>
                  <div className={styles.comment}>{item.comment}</div>
                </>
              )}

              <div className={styles.label}>{admin.dislikedSources}</div>
              {titles.length > 0 ? (
                <div className={styles.sources}>
                  {titles.map((title) => (
                    <span key={title} className={styles.source} title={title}>{title}</span>
                  ))}
                </div>
              ) : (
                <div className={styles.noSources}>{admin.dislikedNoSources}</div>
              )}

              <footer className={styles.cardFoot}>
                <button
                  type="button"
                  className={item.reviewed ? styles.reopenBtn : styles.reviewBtn}
                  disabled={busyId === item.id}
                  onClick={() => void setReviewed(item, !item.reviewed)}
                >
                  {item.reviewed ? admin.dislikedReopen : admin.dislikedMarkReviewed}
                </button>
              </footer>
            </article>
          );
        })}
      </div>
    </div>
  );
}
