import { useMemo, useState } from "react";
import { FaCalculator } from "react-icons/fa6";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import { ACCENT, PRIMARY, PRIMARY_ON_DARK } from "./theme";
import styles from "./CalculatorModal.module.css";

interface CalculatorModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

type Mode = "credit" | "deposit";

// Raqamni bo'sh joy bilan guruhlaydi: 1234567 -> "1 234 567"
const groupNum = (n: number): string =>
  Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");

// Faqat raqamlarni qoldiradi (input tahrirlashda)
const parseNum = (s: string): number => {
  const digits = s.replace(/[^\d]/g, "");
  return digits ? Number(digits) : 0;
};

const clamp = (v: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, v));

interface FieldConfig {
  min: number;
  max: number;
  step: number;
}

const AMOUNT: FieldConfig = { min: 1_000_000, max: 500_000_000, step: 1_000_000 };
const RATE: FieldConfig = { min: 0, max: 40, step: 0.5 };
const MONTHS: FieldConfig = { min: 1, max: 84, step: 1 };

export default function CalculatorModal({ tk, isDark, s, onClose }: CalculatorModalProps) {
  const [mode, setMode] = useState<Mode>("credit");
  const [amount, setAmount] = useState(50_000_000);
  const [rate, setRate] = useState(24);
  const [months, setMonths] = useState(24);

  const accent = isDark ? PRIMARY_ON_DARK : PRIMARY;

  // Hisob-kitob (kirish o'zgarsa qayta hisoblanadi)
  const result = useMemo(() => {
    if (mode === "credit") {
      // Annuitet oylik to'lov: M = P*r*(1+r)^n / ((1+r)^n - 1)
      const r = rate / 100 / 12;
      const n = months;
      const monthly = r === 0 ? amount / n : (amount * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      const totalPaid = monthly * n;
      return { monthly, totalPaid, overpay: totalPaid - amount };
    }
    // Omonat: oddiy foiz — foyda = P * stavka% * (oy/12)
    const profit = amount * (rate / 100) * (months / 12);
    return { profit, total: amount + profit };
  }, [mode, amount, rate, months]);

  // Slayder to'ldirilgan qismini aksent rangda ko'rsatish uchun gradient
  const fill = (val: number, cfg: FieldConfig): string => {
    const pct = ((val - cfg.min) / (cfg.max - cfg.min)) * 100;
    return `linear-gradient(to right, ${accent} 0%, ${accent} ${pct}%, ${tk.cardBorder} ${pct}%, ${tk.cardBorder} 100%)`;
  };

  const cardBg = isDark ? "rgba(255,255,255,.05)" : "#f4f6f9";

  const field = (
    label: string,
    value: number,
    setValue: (v: number) => void,
    cfg: FieldConfig,
    opts: { small?: boolean; suffix?: string; decimals?: boolean } = {}
  ) => (
    <div className={styles.field}>
      <div className={styles.fieldTop}>
        <span className={styles.label} style={{ color: tk.muted }}>{label}</span>
        <span className={styles.valueBox}>
          <input
            className={`${styles.valueInput} ${opts.small ? styles.valueInputSm : ""}`}
            style={{ color: tk.strong }}
            value={opts.decimals ? String(value) : groupNum(value)}
            onChange={(e) => {
              const raw = opts.decimals
                ? Number(e.target.value.replace(/[^\d.]/g, "")) || 0
                : parseNum(e.target.value);
              setValue(clamp(raw, cfg.min, cfg.max));
            }}
            inputMode={opts.decimals ? "decimal" : "numeric"}
          />
          {opts.suffix && <span className={styles.suffix} style={{ color: tk.muted }}>{opts.suffix}</span>}
        </span>
      </div>
      <input
        type="range"
        className={styles.range}
        min={cfg.min}
        max={cfg.max}
        step={cfg.step}
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
        style={{ background: fill(value, cfg), ["--calc-accent" as string]: accent }}
      />
    </div>
  );

  const amountLabel = mode === "credit" ? s.calcCreditAmount : s.calcDepositAmount;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>
            <FaCalculator size={17} color={accent} />
            {s.calcHeading}
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

        <div className={styles.tabs} style={{ background: cardBg }}>
          {(["credit", "deposit"] as Mode[]).map((m) => {
            const active = mode === m;
            return (
              <button
                key={m}
                className={styles.tab}
                onClick={() => setMode(m)}
                style={{
                  background: active ? tk.card : "transparent",
                  color: active ? accent : tk.muted,
                  boxShadow: active ? "0 2px 8px rgba(9,20,34,.14)" : "none",
                }}
              >
                {m === "credit" ? s.calcTabCredit : s.calcTabDeposit}
              </button>
            );
          })}
        </div>

        {field(amountLabel, amount, setAmount, AMOUNT, { suffix: s.calcCurrency })}
        {field(s.calcRate, rate, setRate, RATE, { small: true, suffix: "%", decimals: true })}
        {field(s.calcMonths, months, setMonths, MONTHS, { small: true, suffix: s.calcUnitMonths })}

        <div className={styles.results} style={{ background: cardBg }}>
          {mode === "credit" ? (
            <>
              <div className={styles.resultMain}>
                <span className={styles.resultMainLabel} style={{ color: tk.muted }}>{s.calcMonthly}</span>
                <span className={styles.resultMainValue} style={{ color: accent }}>
                  {groupNum(result.monthly ?? 0)} {s.calcCurrency}
                </span>
              </div>
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcTotalPaid}</span>
                <span className={styles.resultRowValue} style={{ color: tk.strong }}>
                  {groupNum(result.totalPaid ?? 0)} {s.calcCurrency}
                </span>
              </div>
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcOverpay}</span>
                <span className={styles.resultRowValue} style={{ color: ACCENT }}>
                  {groupNum(result.overpay ?? 0)} {s.calcCurrency}
                </span>
              </div>
            </>
          ) : (
            <>
              <div className={styles.resultMain}>
                <span className={styles.resultMainLabel} style={{ color: tk.muted }}>{s.calcTotal}</span>
                <span className={styles.resultMainValue} style={{ color: accent }}>
                  {groupNum(result.total ?? 0)} {s.calcCurrency}
                </span>
              </div>
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcProfit}</span>
                <span className={styles.resultRowValue} style={{ color: "#2f9e6f" }}>
                  + {groupNum(result.profit ?? 0)} {s.calcCurrency}
                </span>
              </div>
            </>
          )}
        </div>

        <div className={styles.note} style={{ color: tk.muted }}>{s.calcNote}</div>
      </div>
    </div>
  );
}
