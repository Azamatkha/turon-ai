import { useMemo } from "react";
import { createPortal } from "react-dom";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import type { PayMethod } from "./CalculatorModal";
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

// Summani "1 234 567.89" ko'rinishida (2 kasr xona, bo'shliq bilan)
const fmt2 = (n: number): string => {
  const fixed = n.toFixed(2);
  const [intPart, dec] = fixed.split(".");
  const neg = intPart.startsWith("-");
  const digits = neg ? intPart.slice(1) : intPart;
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${neg ? "-" : ""}${grouped}.${dec}`;
};

const addMonths = (date: Date, m: number): Date => {
  const d = new Date(date);
  d.setMonth(d.getMonth() + m);
  return d;
};

const fmtDate = (d: Date): string => {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}.${mm}.${d.getFullYear()}`;
};

interface Row {
  k: number;
  date: string;
  balance: number;
  principalPay: number;
  interest: number;
  total: number;
  days: number;
}

export default function PaymentScheduleModal({ principal, rate, months, method, tk, isDark, s, onClose }: Props) {
  const accent = isDark ? PRIMARY_ON_DARK : PRIMARY;

  const { rows, totalPrincipal, totalInterest, totalPaid } = useMemo(() => {
    const r = rate / 100 / 12;
    const n = Math.max(1, months);
    const annuityPay = r === 0 ? principal / n : (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    const flatInterestPer = (principal * (rate / 100) * (n / 12)) / n;

    const start = new Date();
    let prev = start;
    let balance = principal;
    let tInterest = 0;
    const out: Row[] = [];

    for (let k = 1; k <= n; k++) {
      const date = addMonths(start, k);
      const days = Math.round((date.getTime() - prev.getTime()) / 86_400_000);
      const bal = balance;
      let interest: number;
      let principalPay: number;
      if (method === "annuity") {
        interest = bal * r;
        principalPay = annuityPay - interest;
      } else if (method === "diff") {
        principalPay = principal / n;
        interest = bal * r;
      } else {
        principalPay = principal / n;
        interest = flatInterestPer;
      }
      if (k === n) principalPay = bal; // oxirgi oy — qoldiqni to'liq yopamiz
      const total = principalPay + interest;
      tInterest += interest;
      out.push({ k, date: fmtDate(date), balance: bal, principalPay, interest, total, days });
      balance = bal - principalPay;
      prev = date;
    }
    return { rows: out, totalPrincipal: principal, totalInterest: tInterest, totalPaid: principal + tInterest };
  }, [principal, rate, months, method]);

  const border = tk.cardBorder;
  const headBg = isDark ? "rgba(255,255,255,.06)" : "#eef2f6";

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${border}` }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head} style={{ borderBottom: `1px solid ${border}` }}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>{s.calcSchedule}</div>
          <button
            className={styles.closeBtn}
            style={{ color: tk.muted }}
            onClick={onClose}
            aria-label={s.close}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
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
              {rows.map((row) => (
                <tr key={row.k} style={{ color: tk.strong, borderTop: `1px solid ${border}` }}>
                  <td style={{ color: tk.muted }}>{row.k}</td>
                  <td>{row.date}</td>
                  <td>{fmt2(row.balance)}</td>
                  <td>{fmt2(row.principalPay)}</td>
                  <td>{fmt2(row.interest)}</td>
                  <td style={{ fontWeight: 600 }}>{fmt2(row.total)}</td>
                  <td style={{ color: tk.muted }}>{row.days}</td>
                </tr>
              ))}
              <tr className={styles.totalRow} style={{ color: accent, borderTop: `2px solid ${border}` }}>
                <td colSpan={2}>{s.schTotalRow}</td>
                <td>—</td>
                <td>{fmt2(totalPrincipal)}</td>
                <td>{fmt2(totalInterest)}</td>
                <td>{fmt2(totalPaid)}</td>
                <td></td>
              </tr>
            </tbody>
          </table>

          <div className={styles.summary} style={{ color: tk.muted }}>
            <div className={styles.summaryRow}>
              <span>{s.calcTotalPaid}</span>
              <span className={styles.summaryVal} style={{ color: tk.strong }}>{fmt2(totalPaid)} {s.calcCurrency}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>{s.calcOverpay}</span>
              <span className={styles.summaryVal} style={{ color: accent }}>{fmt2(totalInterest)} {s.calcCurrency}</span>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
