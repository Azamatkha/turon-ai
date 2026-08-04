import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FilterSelect from "./FilterSelect";
import ReportDetailModal from "./ReportDetailModal";
import {
  getReport,
  listReports,
  type ApiReportAdmin,
  type ReportStatus,
} from "../../services/reportService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./ReportsView.module.css";

interface ReportsViewProps {
  mounted: boolean;
  t: AdminStrings;
  // Sidebar'dagi "yangi" belgisi ro'yxat bilan bir xil turishi uchun
  onCountsChange?: (newCount: number) => void;
}

export function statusLabel(status: ReportStatus, admin: AdminStrings): string {
  if (status === "in_progress") return admin.reportStatusInProgress;
  if (status === "resolved") return admin.reportStatusResolved;
  return admin.reportStatusNew;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ReportsView({ mounted, t: admin, onCountsChange }: ReportsViewProps) {
  const [items, setItems] = useState<ApiReportAdmin[]>([]);
  const [status, setStatus] = useState<ReportStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApiReportAdmin | null>(null);
  // Bildirishnomadan kelingan bo'lsa manzilda ?report=<id> turadi
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkId = searchParams.get("report");

  const clearDeepLink = useCallback(() => {
    if (!deepLinkId) return;
    const next = new URLSearchParams(searchParams);
    next.delete("report");
    setSearchParams(next, { replace: true });
  }, [deepLinkId, searchParams, setSearchParams]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listReports({ status, size: 100 });
      setItems(data.items);
      setErr(null);
      onCountsChange?.(data.new_count);
    } catch (e) {
      setItems([]);
      setErr(e instanceof Error ? e.message : admin.reportsLoadError);
    } finally {
      setLoading(false);
    }
    // onCountsChange AdminPage'da har renderda yangi bo'lmasin uchun useCallback bilan keladi
  }, [status, admin.reportsLoadError, onCountsChange]);

  useEffect(() => {
    void load();
  }, [load]);

  // ?report=<id> bo'lsa o'sha murojaat alohida so'raladi va darhol ochiladi.
  // Ro'yxatdan qidirilmaydi — u filtr/sahifadan tashqarida bo'lishi mumkin.
  useEffect(() => {
    if (!deepLinkId) return;
    let alive = true;
    getReport(deepLinkId)
      .then((r) => {
        if (alive) setSelected(r);
      })
      .catch(() => {
        if (alive) {
          setErr(admin.reportsLoadError);
          clearDeepLink();
        }
      });
    return () => {
      alive = false;
    };
  }, [deepLinkId, admin.reportsLoadError, clearDeepLink]);

  const statusOptions = [
    { value: "", label: admin.reportFilterAll },
    { value: "new", label: admin.reportStatusNew },
    { value: "in_progress", label: admin.reportStatusInProgress },
    { value: "resolved", label: admin.reportStatusResolved },
  ];

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <FilterSelect
          value={status}
          onChange={(v) => setStatus(v as ReportStatus | "")}
          options={statusOptions}
        />
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.card}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span className={styles.colDate}>{admin.reportColDate}</span>
          <span className={styles.colUser}>{admin.reportColUser}</span>
          <span className={styles.colKind}>{admin.reportColKind}</span>
          <span className={styles.colTitle}>{admin.reportColTitle}</span>
          <span className={styles.colStatus}>{admin.reportColStatus}</span>
        </div>

        {!loading && items.length === 0 && (
          <div className={styles.empty}>{admin.reportsEmpty}</div>
        )}

        {items.map((r) => (
          <button
            key={r.id}
            type="button"
            className={`${styles.row} ${styles.dataRow}`}
            onClick={() => setSelected(r)}
          >
            <span className={styles.colDate}>{fmtDate(r.created_at)}</span>
            <span className={styles.colUser}>
              {r.user_name}
              {r.user_department && (
                <span className={styles.dept}>{r.user_department}</span>
              )}
            </span>
            <span className={styles.colKind}>
              {r.kind === "problem" ? admin.reportKindProblem : admin.reportKindSuggestion}
            </span>
            <span className={styles.colTitle}>
              {r.title}
              {r.has_screenshot && <span className={styles.clip} aria-hidden="true">📎</span>}
            </span>
            <span className={styles.colStatus}>
              <span className={`${styles.badge} ${styles[`st_${r.status}`]}`}>
                {statusLabel(r.status, admin)}
              </span>
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <ReportDetailModal
          report={selected}
          t={admin}
          onClose={() => {
            setSelected(null);
            clearDeepLink();
          }}
          onSaved={(updated) => {
            setItems((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
            setSelected(null);
            clearDeepLink();
            void load();
          }}
        />
      )}
    </div>
  );
}
