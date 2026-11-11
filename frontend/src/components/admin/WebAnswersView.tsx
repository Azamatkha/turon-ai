import { useCallback, useEffect, useState } from "react";
import { listWebAnswers, type WebAnswer } from "../../services/adminService";
import { scrapeUrl } from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./SafetyView.module.css";

interface WebAnswersViewProps {
  mounted: boolean;
  t: AdminStrings;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Bazada yo'q, ruxsat etilgan saytdan javob berilgan savollar. Admin sahifani
// bir bosishda bilim bazasiga qo'shadi — keyingi safar javob bazadan keladi.
export default function WebAnswersView({ mounted, t: admin }: WebAnswersViewProps) {
  const [items, setItems] = useState<WebAnswer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  // URL -> holat: "busy" | "done" | xato matni
  const [added, setAdded] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listWebAnswers(200);
      setItems(data.items);
      setTotal(data.total);
      setErr(null);
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.webLoadError);
    } finally {
      setLoading(false);
    }
  }, [admin.webLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const addToKb = async (url: string) => {
    setAdded((a) => ({ ...a, [url]: "busy" }));
    try {
      await scrapeUrl(url);
      setAdded((a) => ({ ...a, [url]: "done" }));
    } catch (e) {
      setAdded((a) => ({ ...a, [url]: (e instanceof Error && e.message) || admin.webAddError }));
    }
  };

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <p className={styles.hint}>{admin.webHint}</p>
      <div className={styles.toolbar}>
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
        <span className={styles.total}>{admin.faceLogsTotal(total)}</span>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.card}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span>{admin.reportColDate}</span>
          <span>{admin.reportColUser}</span>
          <span>{admin.webColSources}</span>
          <span>{admin.safetyColQuestion}</span>
        </div>
        {!loading && items.length === 0 && !err && <div className={styles.empty}>{admin.webEmpty}</div>}
        {items.map((q) => (
          <div key={q.id} className={styles.row}>
            <span className={styles.date}>{fmtDate(q.created_at)}</span>
            <span className={styles.user}>
              <span className={styles.name}>{q.user_name || "—"}</span>
              {q.username && <span className={styles.handle}>@{q.username}</span>}
            </span>
            <span className={styles.links}>
              {q.source_urls.map((url) => {
                const st = added[url];
                return (
                  <span key={url} className={styles.linkRow}>
                    <a href={url} target="_blank" rel="noopener noreferrer" className={styles.link} title={url}>
                      {domainOf(url)}
                    </a>
                    {st === "done" ? (
                      <span className={styles.addedNote}>{admin.webAdded}</span>
                    ) : (
                      <button
                        type="button"
                        className={styles.addBtn}
                        disabled={st === "busy"}
                        onClick={() => void addToKb(url)}
                      >
                        {admin.webAddToKb}
                      </button>
                    )}
                    {st && st !== "busy" && st !== "done" && <span className={styles.addErr}>{st}</span>}
                  </span>
                );
              })}
            </span>
            <span className={styles.question}>{q.question}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
