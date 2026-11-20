import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import { listAuditLogs, type AuditLogItem, type AuditSort } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import { pageList } from "../../utils/pageList";
import styles from "./AuditLogsView.module.css";

const PAGE_SIZE = 50;

interface AuditLogsViewProps {
  mounted: boolean;
  t: AdminStrings;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// Amal turi bo'yicha rang: o'chirish — qizil, yaratish/yuklash — yashil, qolgan — ko'k
function actionTone(action: string): string {
  if (action.endsWith(".delete")) return styles.toneDanger;
  if (/\.(create|upload|pdf|employees|scrape)$/.test(action)) return styles.toneSuccess;
  return styles.toneInfo;
}

// details qiymatini qisqa matnga aylantiradi
function fmtValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.map(fmtValue).join(", ") || "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// Admin amallari jurnali: kim, nima qildi, nimaga, qachon. Faqat o'qish uchun.
export default function AuditLogsView({ mounted, t: admin }: AuditLogsViewProps) {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [targetType, setTargetType] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<AuditSort>("newest");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  // Qidiruv har harfda so'rov yubormasin — 350ms kutamiz
  useEffect(() => {
    const id = window.setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(id);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAuditLogs({ targetType, search: query, sort, page, size: PAGE_SIZE });
      setItems(data.items);
      setTotal(data.total);
      setErr(null);
    } catch (e) {
      setItems([]);
      setTotal(0);
      setErr((e instanceof Error && e.message) || admin.auditLoadError);
    } finally {
      setLoading(false);
    }
  }, [targetType, query, sort, page, admin.auditLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const actionLabel = (a: string) => admin.auditActions[a] ?? a;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <FilterSelect
          value={targetType}
          onChange={(v) => {
            setTargetType(v);
            setPage(1);
          }}
          options={[
            { value: "", label: admin.auditTypeAll },
            { value: "user", label: admin.auditTypeUser },
            { value: "knowledge", label: admin.auditTypeKnowledge },
            { value: "report", label: admin.auditTypeReport },
            { value: "guide", label: admin.auditTypeGuide },
            { value: "message", label: admin.auditTypeMessage },
          ]}
        />
        <FilterSelect
          value={sort}
          onChange={(v) => {
            setSort(v as AuditSort);
            setPage(1);
          }}
          options={(["newest", "oldest", "actor", "action"] as const).map((k) => ({ value: k, label: admin.auditSort[k] }))}
        />
        <input
          className={styles.search}
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={admin.auditSearchPh}
          aria-label={admin.auditSearchPh}
        />
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
        <span className={styles.total}>{admin.faceLogsTotal(total)}</span>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.card}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span>{admin.reportColDate}</span>
          <span>{admin.auditColActor}</span>
          <span>{admin.auditColAction}</span>
          <span>{admin.auditColTarget}</span>
          <span>IP</span>
        </div>

        {!loading && items.length === 0 && !err && <div className={styles.empty}>{admin.auditEmpty}</div>}

        {items.map((it) => {
          const open = openId === it.id;
          const details = it.details ? Object.entries(it.details) : [];
          return (
            <div key={it.id} className={styles.entry}>
              <button
                type="button"
                className={`${styles.row} ${styles.dataRow}`}
                onClick={() => setOpenId(open ? null : it.id)}
                aria-expanded={open}
                disabled={details.length === 0}
              >
                <span className={styles.colDate}>{fmtDate(it.created_at)}</span>
                <span className={styles.colActor}>@{it.actor_username}</span>
                <span>
                  <span className={`${styles.badge} ${actionTone(it.action)}`}>{actionLabel(it.action)}</span>
                </span>
                <span className={styles.colTarget} title={it.target_label || it.target_id || ""}>
                  {it.target_label || it.target_id || "—"}
                </span>
                <span className={styles.colIp}>{it.ip || "—"}</span>
              </button>
              {open && details.length > 0 && (
                <dl className={styles.details}>
                  {details.map(([k, v]) => (
                    <div key={k} className={styles.detailRow}>
                      <dt>{admin.auditFields[k] ?? k}</dt>
                      <dd>{fmtValue(v)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          );
        })}

        {total > PAGE_SIZE && (
          <nav className={styles.pager} aria-label={admin.pageRange(start + 1, start + items.length, total)}>
            <span className={styles.pagerInfo}>{admin.pageRange(start + 1, start + items.length, total)}</span>
            <div className={styles.pagerBtns}>
              <button type="button" className={styles.pageBtn} onClick={() => setPage(page - 1)} disabled={page === 1 || loading} aria-label={admin.pagePrev}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              {pageList(page, totalPages).map((p, i) =>
                p === null ? (
                  <span key={`gap-${i}`} className={styles.pageGap}>…</span>
                ) : (
                  <button key={p} type="button" className={`${styles.pageBtn} ${p === page ? styles.pageBtnActive : ""}`} onClick={() => setPage(p)} disabled={loading} aria-current={p === page ? "page" : undefined}>
                    {p}
                  </button>
                )
              )}
              <button type="button" className={styles.pageBtn} onClick={() => setPage(page + 1)} disabled={page === totalPages || loading} aria-label={admin.pageNext}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
              </button>
            </div>
          </nav>
        )}
      </div>
    </div>
  );
}
