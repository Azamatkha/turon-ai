import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import { listAuditLogs, type AuditLogItem } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./AuditLogsView.module.css";

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
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  // Qidiruv har harfda so'rov yubormasin — 350ms kutamiz
  useEffect(() => {
    const id = window.setTimeout(() => setQuery(search), 350);
    return () => window.clearTimeout(id);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAuditLogs({ targetType, search: query, size: 200 });
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
  }, [targetType, query, admin.auditLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const actionLabel = (a: string) => admin.auditActions[a] ?? a;

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <FilterSelect
          value={targetType}
          onChange={setTargetType}
          options={[
            { value: "", label: admin.auditTypeAll },
            { value: "user", label: admin.auditTypeUser },
            { value: "knowledge", label: admin.auditTypeKnowledge },
            { value: "report", label: admin.auditTypeReport },
            { value: "guide", label: admin.auditTypeGuide },
            { value: "message", label: admin.auditTypeMessage },
          ]}
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
      </div>
    </div>
  );
}
