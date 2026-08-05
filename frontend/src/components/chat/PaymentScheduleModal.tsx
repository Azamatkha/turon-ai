import { useMemo } from "react";
import { createPortal } from "react-dom";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import {
  buildSchedule,
  downloadSchedule,
  scheduleFileName,
  fmt2,
  fmtDate,
  type PayMethod,
} from "../../utils/paymentSchedule";
import { PRIMARY, PRIMARY_ON_DARK } from "./theme";
import styles from "./PaymentScheduleModal.module.css";

interface Props {
  principal: number;
  rate: number;
  months: number;
  method: PayMethod;
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

export default function PaymentScheduleModal({
  principal, rate, months, method, tk, isDark, s, onClose,
}: Props) {
  const accent = isDark ? PRIMARY_ON_DARK : PRIMARY;
  const res = useMemo(
    () => buildSchedule(principal, rate, months, method),
    [principal, rate, months, method]
  );

  const border = tk.cardBorder;
  const headBg = isDark ? "rgba(255,255,255,.06)" : "#F1F5F9";

  const download = () =>
    downloadSchedule(
      res,
      {
        title: s.calcSchedule,
        no: s.schNo,
        date: s.schDate,
        balance: s.schBalance,
        principal: s.schPrincipal,
        interest: s.schInterest,
        total: s.schTotal,
        days: s.schDays,
        totalRow: s.schTotalRow,
        insurance: s.schInsurance,
        fullCost: s.schFullCost,
        currency: s.calcCurrency,
      },
      scheduleFileName()
    );

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${border}` }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head} style={{ borderBottom: `1px solid ${border}` }}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>{s.calcSchedule}</div>
          <div className={styles.headActions}>
            <button
              className={styles.dlBtn}
              style={{ background: accent }}
              onClick={download}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
              {s.calcScheduleDownload}
            </button>
            <button
              className={styles.closeBtn}
              style={{ color: tk.muted }}
              onClick={onClose}
              aria-label={s.close}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
            </button>
          </div>
        </div>

        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr style={{ color: tk.muted }}>
                <th style={{ background: headBg }}>{s.schNo}</th>
                <th style={{ background: headBg }}>{s.schDate}</th>
                <th style={{ background: headBg }}>{s.schBalance}</th>
                <th style={{ background: headBg }}>{s.schPrincipal}</th>
                <th style={{ background: headBg }}>{s.schInterest}</th>
                <th style={{ background: headBg }}>{s.schTotal}</th>
                <th style={{ background: headBg }}>{s.schDays}</th>
              </tr>
            </thead>
            <tbody>
              {res.rows.map((row) => (
                <tr key={row.k} style={{ color: tk.strong, borderTop: `1px solid ${border}` }}>
                  <td style={{ color: tk.muted }}>{row.k}</td>
                  <td>{fmtDate(row.date)}</td>
                  <td>{fmt2(row.balance)}</td>
                  <td>{fmt2(row.principal)}</td>
                  <td>{fmt2(row.interest)}</td>
                  <td style={{ fontWeight: 600 }}>{fmt2(row.total)}</td>
                  <td style={{ color: tk.muted }}>{row.days}</td>
                </tr>
              ))}
              <tr className={styles.totalRow} style={{ color: accent, borderTop: `2px solid ${border}` }}>
                <td colSpan={3}>{s.schTotalRow}</td>
                <td>{fmt2(res.totalPrincipal)}</td>
                <td>{fmt2(res.totalInterest)}</td>
                <td>{fmt2(res.totalPaid)}</td>
                <td />
              </tr>
            </tbody>
          </table>

          <div className={styles.summary} style={{ color: tk.muted }}>
            <div className={styles.summaryRow}>
              <span>{s.schInsurance}</span>
              <span className={styles.summaryVal} style={{ color: tk.strong }}>
                {fmt2(res.insurance)} {s.calcCurrency}
              </span>
            </div>
            <div className={styles.summaryRow}>
              <span>{s.schFullCost}</span>
              <span className={styles.summaryVal} style={{ color: accent }}>
                {fmt2(res.fullCost)} {s.calcCurrency}
              </span>
            </div>
          </div>

          <div className={styles.note} style={{ color: tk.muted }}>{s.calcNote}</div>
        </div>
      </div>
    </div>,
    document.body
  );
}
