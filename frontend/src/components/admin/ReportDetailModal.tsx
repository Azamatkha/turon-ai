import { useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import {
  fetchReportScreenshot,
  updateReport,
  type ApiReportAdmin,
  type ReportStatus,
} from "../../services/reportService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./ReportDetailModal.module.css";

interface ReportDetailModalProps {
  report: ApiReportAdmin;
  t: AdminStrings;
  onClose: () => void;
  onSaved: (updated: ApiReportAdmin) => void;
}

export default function ReportDetailModal({
  report,
  t: admin,
  onClose,
  onSaved,
}: ReportDetailModalProps) {
  const [status, setStatus] = useState<ReportStatus>(report.status);
  const [comment, setComment] = useState(report.admin_comment);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [shot, setShot] = useState<string | null>(null);
  const [shotErr, setShotErr] = useState(false);

  // Skrinshot ochiq URL'da turmaydi — himoyalangan endpointdan blob olinadi
  useEffect(() => {
    if (!report.has_screenshot) return;
    let url: string | null = null;
    let alive = true;
    fetchReportScreenshot(report.id)
      .then((objectUrl) => {
        url = objectUrl;
        if (alive) setShot(objectUrl);
        else URL.revokeObjectURL(objectUrl);
      })
      .catch(() => {
        if (alive) setShotErr(true);
      });
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [report.id, report.has_screenshot]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const save = async () => {
    setSaving(true);
    setErr(null);
    try {
      onSaved(await updateReport(report.id, status, comment));
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.reportSaveError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.head}>
          <div>
            <div className={styles.title}>{admin.reportDetail}</div>
            <div className={styles.sub}>
              {report.user_name}
              {report.user_department ? ` · ${report.user_department}` : ""}
              {" · "}
              {report.kind === "problem"
                ? admin.reportKindProblem
                : admin.reportKindSuggestion}
            </div>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="×">
            ×
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.reportTitle}>{report.title}</div>
          <div className={styles.description}>{report.description}</div>

          <div className={styles.section}>
            <span className={styles.label}>{admin.reportScreenshotLabel}</span>
            {!report.has_screenshot && (
              <div className={styles.muted}>{admin.reportNoScreenshot}</div>
            )}
            {report.has_screenshot && shotErr && (
              <div className={styles.muted}>{admin.reportScreenshotError}</div>
            )}
            {shot && (
              <a href={shot} target="_blank" rel="noreferrer">
                <img className={styles.shot} src={shot} alt="" />
              </a>
            )}
          </div>

          <div className={styles.section}>
            <span className={styles.label}>{admin.reportColStatus}</span>
            <FilterSelect
              value={status}
              onChange={(v) => setStatus(v as ReportStatus)}
              fullWidth
              options={[
                { value: "new", label: admin.reportStatusNew },
                { value: "in_progress", label: admin.reportStatusInProgress },
                { value: "resolved", label: admin.reportStatusResolved },
              ]}
            />
          </div>

          <div className={styles.section}>
            <span className={styles.label}>{admin.reportComment}</span>
            <textarea
              className={styles.textarea}
              value={comment}
              maxLength={5000}
              placeholder={admin.reportCommentPh}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>

          {err && <div className={styles.error}>{err}</div>}

          <button
            type="button"
            className={styles.saveBtn}
            disabled={saving}
            onClick={() => void save()}
          >
            {admin.reportSave}
          </button>
        </div>
      </div>
    </div>
  );
}
