import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { MdCurrencyExchange } from "react-icons/md";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { fetchRates, type RateRow, type RatesResult } from "../../services/ratesService";
import { ACCENT, PRIMARY_ON_DARK } from "./theme";
import styles from "./RatesModal.module.css";

interface RatesModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

// O'sish/tushish ranglari — mavzudan qat'i nazar bir xil ma'noda o'qiladi.
const UP = "#16A34A";
const DOWN = "#DC2626";

// 11850 -> "11 850", 11934.61 -> "11 934,61"
function money(n: number): string {
  const whole = Math.trunc(Math.abs(n));
  const frac = Math.round((Math.abs(n) - whole) * 100);
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const text = frac ? `${grouped},${frac.toString().padStart(2, "0")}` : grouped;
  return n < 0 ? `-${text}` : text;
}

/** Qiymat + uning o'zgarishi. Qiymat bo'lmasa chiziqcha ko'rsatiladi —
 *  ilova va bankomat jadvallarida ba'zi valyutalar bo'yicha sotish kursi
 *  umuman e'lon qilinmaydi. */
function Cell({ value, delta, muted }: { value: number | null; delta: number | null; muted: string }) {
  if (value === null) {
    return <span style={{ color: muted }}>—</span>;
  }
  return (
    <span className={styles.cellValue}>
      {money(value)}
      {delta ? (
        <span className={styles.delta} style={{ color: delta > 0 ? UP : DOWN }}>
          {delta > 0 ? "▲" : "▼"} {money(Math.abs(delta))}
        </span>
      ) : null}
    </span>
  );
}

export default function RatesModal({ tk, isDark, s, onClose }: RatesModalProps) {
  const accent = isDark ? PRIMARY_ON_DARK : ACCENT;
  const cardBg = isDark ? "rgba(255,255,255,.06)" : "#F1F5F9";

  const [data, setData] = useState<RatesResult | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    let alive = true;
    fetchRates()
      .then((r) => alive && setData(r))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, []);

  // Esc bilan yopish — qolgan oynalarda ham shunday.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const channels = data?.channels ?? [];
  const rows: RateRow[] = useMemo(
    () => channels[tab]?.rows ?? [],
    [channels, tab],
  );

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.scroll}>
          <div className={styles.head}>
            <div className={styles.headTitle} style={{ color: tk.strong }}>
              <MdCurrencyExchange size={19} color={accent} />
              {s.ratesHeading}
            </div>
            <button
              className={styles.closeBtn}
              style={{ color: tk.muted }}
              onClick={onClose}
              aria-label={s.close}
              onMouseEnter={(e) => (e.currentTarget.style.background = cardBg)}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
            </button>
          </div>

          {error || (data && channels.length === 0) ? (
            <div className={styles.empty} style={{ color: tk.muted }}>
              {error ? s.ratesError : s.ratesEmpty}
            </div>
          ) : !data ? (
            <div className={styles.empty} style={{ color: tk.muted }}>
              {s.ratesLoading}
            </div>
          ) : (
            <>
              {data.stamp && (
                <div className={styles.stamp} style={{ color: tk.muted }}>
                  {data.stamp}
                </div>
              )}

              <div className={styles.tabs} style={{ background: cardBg }}>
                {channels.map((c, i) => (
                  <button
                    key={c.key}
                    className={styles.tab}
                    onClick={() => setTab(i)}
                    style={{
                      background: i === tab ? tk.card : "transparent",
                      color: i === tab ? accent : tk.muted,
                      boxShadow: i === tab ? "0 2px 8px rgba(15,23,42,.14)" : "none",
                    }}
                  >
                    {c.label}
                  </button>
                ))}
              </div>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr style={{ color: tk.muted }}>
                      <th className={styles.thLeft}>{s.ratesCurrency}</th>
                      <th>{s.ratesBuy}</th>
                      <th>{s.ratesSell}</th>
                      <th>{s.ratesCb}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.code} style={{ borderTop: `1px solid ${tk.cardBorder}` }}>
                        <td className={styles.thLeft}>
                          <div className={styles.code} style={{ color: tk.strong }}>{r.code}</div>
                          <div className={styles.name} style={{ color: tk.muted }}>{r.name}</div>
                        </td>
                        <td style={{ color: tk.strong }}>
                          <Cell value={r.buy} delta={r.delta_buy} muted={tk.muted} />
                        </td>
                        <td style={{ color: tk.strong }}>
                          <Cell value={r.sell} delta={r.delta_sell} muted={tk.muted} />
                        </td>
                        <td style={{ color: tk.strong }}>
                          <Cell value={r.cb} delta={r.delta_cb} muted={tk.muted} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className={styles.note} style={{ color: tk.muted }}>
                {s.ratesDeltaNote}
              </div>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
