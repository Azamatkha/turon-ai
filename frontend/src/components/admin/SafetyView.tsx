import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import { listFlaggedQuestions, type FlaggedQuestion } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./SafetyView.module.css";

interface SafetyViewProps {
  mounted: boolean;
  t: AdminStrings;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Xavfli so'rovlar va so'kinishlar: kim, qachon, nima yozgan. Bot ularga
// javob bermagan — bu ro'yxat admin e'tibori uchun.
export default function SafetyView({ mounted, t: admin }: SafetyViewProps) {
  const [items, setItems] = useState<FlaggedQuestion[]>([]);
  const [total, setTotal] = useState(0);
  const [kind, setKind] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listFlaggedQuestions(200);
      setItems(data.items);
      setTotal(data.total);
      setErr(null);
    } catch (e) {
      setErr((e instanceof Error && e.message) || admin.safetyLoadError);
    } finally {
      setLoading(false);
    }
  }, [admin.safetyLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const kindLabel = (k: string) => (k === "profanity" ? admin.safetyKindProfanity : admin.safetyKindHarmful);
  const shown = kind ? items.filter((i) => i.kind === kind) : items;

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <p className={styles.hint}>{admin.safetyHint}</p>
      <div className={styles.toolbar}>
        <FilterSelect
          value={kind}
          onChange={setKind}
          options={[
            { value: "", label: admin.safetyKindAll },
            { value: "harmful", label: admin.safetyKindHarmful },
            { value: "profanity", label: admin.safetyKindProfanity },
          ]}
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
          <span>{admin.reportColUser}</span>
          <span>{admin.safetyColKind}</span>
          <span>{admin.safetyColQuestion}</span>
        </div>
        {!loading && shown.length === 0 && !err && <div className={styles.empty}>{admin.safetyEmpty}</div>}
        {shown.map((q) => (
          <div key={q.id} className={styles.row}>
            <span className={styles.date}>{fmtDate(q.created_at)}</span>
            <span className={styles.user}>
              <span className={styles.name}>{q.user_name || "—"}</span>
              {q.username && <span className={styles.handle}>@{q.username}</span>}
            </span>
            <span>
              <span className={`${styles.badge} ${q.kind === "profanity" ? styles.badgeWarn : styles.badgeDanger}`}>
                {kindLabel(q.kind)}
              </span>
            </span>
            <span className={styles.question}>{q.question}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
