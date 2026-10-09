import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import { listFaceIdLogs, type ApiFaceIdLog } from "../../services/faceIdLogService";
import type { AdminStrings } from "../../types/i18n";
import { useModalA11y } from "../../hooks/useModalA11y";
import styles from "./FaceIdLogsView.module.css";

interface FaceIdLogsViewProps {
  mounted: boolean;
  t: AdminStrings;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// "ok" — yashil, "not_employee" — sariq, qolgan hammasi (xato sababi) — qizil
function resultClass(result: string): string {
  if (result === "ok") return styles.resOk;
  if (result === "not_employee") return styles.resWarn;
  return styles.resFail;
}

export default function FaceIdLogsView({ mounted, t: admin }: FaceIdLogsViewProps) {
  const [items, setItems] = useState<ApiFaceIdLog[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<"" | "failed">("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApiFaceIdLog | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listFaceIdLogs({ onlyFailed: filter === "failed", size: 100 });
      setItems(data.items);
      setTotal(data.total);
      setErr(null);
    } catch (e) {
      setItems([]);
      setTotal(0);
      setErr((e instanceof Error && e.message) || admin.faceLogsLoadError);
    } finally {
      setLoading(false);
    }
  }, [filter, admin.faceLogsLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  // verificationId holati: bor (yashil) / yo'q (qizil) / token umuman yo'q (qizil)
  const vidBadge = (log: ApiFaceIdLog) => {
    if (log.verification_id) {
      return (
        <span className={`${styles.badge} ${styles.resOk}`} title={log.verification_id}>
          {admin.faceLogsVidPresent}
        </span>
      );
    }
    return (
      <span className={`${styles.badge} ${styles.resFail}`}>
        {log.has_token ? admin.faceLogsVidMissing : admin.faceLogsNoToken}
      </span>
    );
  };

  const close = () => {
    setSelected(null);
    setCopied(false);
  };
  const modalRef = useModalA11y<HTMLDivElement>(close, !!selected);

  const copySignature = async () => {
    if (!selected) return;
    try {
      await navigator.clipboard.writeText(selected.signature);
      setCopied(true);
    } catch {
      /* clipboard yopiq (http yoki ruxsat yo'q) — matnni qo'lda belgilash mumkin */
    }
  };

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <FilterSelect
          value={filter}
          onChange={(v) => setFilter(v as "" | "failed")}
          options={[
            { value: "", label: admin.faceLogsFilterAll },
            { value: "failed", label: admin.faceLogsFilterFailed },
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
          <span>{admin.faceLogsColPerson}</span>
          <span>verificationId</span>
          <span>{admin.faceLogsColResult}</span>
        </div>

        {!loading && items.length === 0 && !err && (
          <div className={styles.empty}>{admin.faceLogsEmpty}</div>
        )}

        {items.map((log) => (
          <button
            key={log.id}
            type="button"
            className={`${styles.row} ${styles.dataRow}`}
            onClick={() => setSelected(log)}
          >
            <span className={styles.colDate}>{fmtDate(log.created_at)}</span>
            <span className={log.username ? styles.colUser : styles.colNoUser}>
              {log.username ? `@${log.username}` : admin.faceLogsNoUser}
            </span>
            <span className={styles.colPerson}>
              {log.person_name || log.pnfl ? (
                <>
                  <span className={styles.personName}>{log.person_name || "—"}</span>
                  {log.pnfl && <span className={styles.personPnfl}>{log.pnfl}</span>}
                </>
              ) : (
                <span className={styles.colNoUser}>{admin.faceLogsNoPerson}</span>
              )}
            </span>
            <span className={styles.colVid}>{vidBadge(log)}</span>
            <span className={styles.colResult}>
              <span className={`${styles.badge} ${resultClass(log.result)}`} title={log.result}>
                {log.result}
              </span>
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <div className={styles.overlay} onClick={close}>
          <div ref={modalRef} role="dialog" aria-modal="true" aria-label={admin.faceLogsDetail} className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.head}>
              <div>
                <div className={styles.title}>{admin.faceLogsDetail}</div>
                <div className={styles.sub}>
                  {fmtDate(selected.created_at)}
                  {" · "}
                  {selected.username ? `@${selected.username}` : admin.faceLogsNoUser}
                  {selected.request_id ? ` · ${selected.request_id}` : ""}
                </div>
              </div>
              <button type="button" className={styles.closeBtn} onClick={close} aria-label={admin.knowledgeCancel}>
                ×
              </button>
            </div>

            <div className={styles.body}>
              <div className={styles.label}>{admin.faceLogsColResult}</div>
              <div className={`${styles.resultBox} ${resultClass(selected.result)}`}>{selected.result}</div>

              <div className={styles.label}>{admin.faceLogsSummary}</div>
              <dl className={styles.summary}>
                <dt>{admin.faceLogsColPerson}</dt>
                <dd>{selected.person_name || "—"}</dd>
                <dt>{admin.faceLogsPnfl}</dt>
                <dd>{selected.pnfl || "—"}</dd>
                <dt>{admin.faceLogsDocument}</dt>
                <dd>{selected.document || "—"}</dd>
                <dt>{admin.faceLogsBirthDate}</dt>
                <dd>{selected.birth_date || "—"}</dd>
                <dt>{admin.faceLogsTokenSub}</dt>
                <dd>{selected.token_sub || (selected.has_token ? "—" : admin.faceLogsNoToken)}</dd>
                <dt>verificationId</dt>
                <dd>
                  {selected.verification_id ||
                    (selected.has_token ? admin.faceLogsVidMissing : admin.faceLogsNoToken)}
                </dd>
              </dl>

              <div className={styles.label}>{admin.faceLogsClaims}</div>
              {selected.claims ? (
                <pre className={styles.code}>{JSON.stringify(selected.claims, null, 2)}</pre>
              ) : (
                <div className={styles.noClaims}>{admin.faceLogsNoClaims}</div>
              )}

              <div className={styles.labelRow}>
                <div className={styles.label}>{admin.faceLogsSignature}</div>
                <button type="button" className={styles.copyBtn} onClick={() => void copySignature()}>
                  {copied ? admin.faceLogsCopied : admin.faceLogsCopy}
                </button>
              </div>
              <pre className={`${styles.code} ${styles.codeWrap}`}>{selected.signature}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
