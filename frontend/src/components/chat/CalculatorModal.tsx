import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
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

type Mode = "credit" | "mortgage" | "deposit";

interface FieldConfig {
  min: number;
  max: number;
  step: number;
}

type PayMethod = "flat" | "annuity" | "diff";

// Oddiy kredit: 6 oydan 60 oygacha (6 oy qadam). Ipoteka/avtokredit: 240 oygacha.
const MONTHS_CREDIT: FieldConfig = { min: 6, max: 60, step: 6 };
const MONTHS_MORTGAGE: FieldConfig = { min: 6, max: 240, step: 6 };
// Omonat: 1 oydan 60 oygacha.
const MONTHS_DEP: FieldConfig = { min: 1, max: 60, step: 1 };
// Foiz: 2 xonali kasr (21.99 kabi) — kiritishda erkin, slayder 0.1 qadam.
const RATE: FieldConfig = { min: 0, max: 50, step: 0.1 };
// Oddiy kredit/omonat summasi: 100 mln gacha. Ipoteka narxi: 500 mln gacha.
const AMOUNT: FieldConfig = { min: 100_000, max: 100_000_000, step: 100_000 };
const PRICE: FieldConfig = { min: 1_000_000, max: 500_000_000, step: 1_000_000 };

// Raqamni bo'sh joy bilan guruhlaydi: 1234567 -> "1 234 567"
const groupNum = (n: number): string =>
  Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");

const clamp = (v: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, v));

// Kredit natijasi to'lov turiga qarab:
//  - flat (ustama): foiz butun summaga, oylar teng;
//  - annuity: har oy teng to'lov, foiz qolgan qarzga;
//  - diff (differensial): asosiy qarz teng, foiz kamayadi -> to'lov kamayib boradi.
function loanResult(principal: number, ratePct: number, months: number, method: PayMethod) {
  const r = ratePct / 100 / 12;
  const n = months || 1;
  let first: number;
  let last: number;
  let totalPaid: number;
  if (method === "annuity") {
    const m = r === 0 ? principal / n : (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    first = m;
    last = m;
    totalPaid = m * n;
  } else if (method === "diff") {
    const principalPart = principal / n;
    first = principalPart + principal * r; // 1-oy: qarz to'liq
    last = principalPart + principalPart * r; // oxirgi oy: qarz eng kam
    totalPaid = principal + r * principal * (n + 1) / 2;
  } else {
    const interest = principal * (ratePct / 100) * (n / 12);
    totalPaid = principal + interest;
    first = totalPaid / n;
    last = first;
  }
  return { principal, first, last, totalPaid, overpay: totalPaid - principal, varies: method === "diff" };
}

interface NumFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  cfg: FieldConfig;
  suffix?: string;
  decimals?: boolean;
  tk: ThemeTokens;
  cardBg: string;
  accent: string;
}

// Qiymat inputi + slayder. Tahrirlashda LOKAL matn holati bilan ishlaydi —
// shuning uchun "100000" ni o'chirib qaytadan yozsa ham darrov minimumga
// clamp bo'lib qolmaydi (min faqat blur'da qo'llanadi). Slayder esa doim
// haqiqiy (clamp qilingan) qiymatni ko'rsatadi.
function NumField({ label, value, onChange, cfg, suffix, decimals, tk, cardBg, accent }: NumFieldProps) {
  const [text, setText] = useState<string | null>(null);
  const display = text !== null ? text : decimals ? String(value) : groupNum(value);

  const pct = ((clamp(value, cfg.min, cfg.max) - cfg.min) / (cfg.max - cfg.min)) * 100;
  const fill = `linear-gradient(to right, ${accent} 0%, ${accent} ${pct}%, ${tk.cardBorder} ${pct}%, ${tk.cardBorder} 100%)`;

  const commitText = (raw: string) => {
    if (decimals) {
      // Faqat raqam va bitta nuqta, nuqtadan keyin 2 xona
      const cleaned = raw.replace(/[^\d.]/g, "");
      const m = cleaned.match(/^(\d*)(?:\.(\d{0,2}))?/);
      const shown = m ? m[0] : "";
      setText(shown);
      const num = Number(shown);
      if (shown !== "" && !Number.isNaN(num)) onChange(clamp(num, 0, cfg.max));
    } else {
      // Yozayotganda ham bo'shliq bilan ajratamiz: "100000000" -> "100 000 000"
      const digits = raw.replace(/[^\d]/g, "");
      if (digits === "") {
        setText("");
        return;
      }
      const n = clamp(Number(digits), 0, cfg.max);
      onChange(n);
      setText(groupNum(n));
    }
  };

  const blur = () => {
    // Tahrir tugadi — endi minimumga ham clamp qilamiz va matnni sinxronlaymiz
    onChange(clamp(value, cfg.min, cfg.max));
    setText(null);
  };

  return (
    <div className={styles.field}>
      <span className={styles.label} style={{ color: tk.muted }}>{label}</span>
      <div className={styles.inputBox} style={{ background: cardBg, border: `1px solid ${tk.cardBorder}` }}>
        <input
          className={styles.valueInput}
          style={{ color: tk.strong }}
          value={display}
          onChange={(e) => commitText(e.target.value)}
          onBlur={blur}
          inputMode={decimals ? "decimal" : "numeric"}
        />
        {suffix && <span className={styles.unit} style={{ color: tk.muted }}>{suffix}</span>}
      </div>
      <input
        type="range"
        className={styles.range}
        min={cfg.min}
        max={cfg.max}
        step={cfg.step}
        value={clamp(value, cfg.min, cfg.max)}
        onChange={(e) => {
          setText(null);
          onChange(Number(e.target.value));
        }}
        style={{ background: fill, ["--calc-accent" as string]: accent }}
      />
    </div>
  );
}

export default function CalculatorModal({ tk, isDark, s, onClose }: CalculatorModalProps) {
  const [mode, setMode] = useState<Mode>("credit");
  const [method, setMethod] = useState<PayMethod>("flat");
  const [amount, setAmount] = useState(50_000_000);
  const [price, setPrice] = useState(300_000_000);
  const [down, setDown] = useState(60_000_000);
  const [rate, setRate] = useState(21.99);
  const [months, setMonths] = useState(24);

  const accent = isDark ? PRIMARY_ON_DARK : PRIMARY;
  const cardBg = isDark ? "rgba(255,255,255,.05)" : "#f4f6f9";
  const monthsCfg =
    mode === "deposit" ? MONTHS_DEP : mode === "mortgage" ? MONTHS_MORTGAGE : MONTHS_CREDIT;
  const isLoan = mode === "credit" || mode === "mortgage";
  const cur = s.calcCurrency;

  // Rejim almashganda muddatni yangi qadamga/oraliqqa moslaymiz
  const switchMode = (m: Mode) => {
    if (m === mode) return;
    const cfg = m === "deposit" ? MONTHS_DEP : m === "mortgage" ? MONTHS_MORTGAGE : MONTHS_CREDIT;
    setMonths((v) => clamp(Math.round(v / cfg.step) * cfg.step || cfg.min, cfg.min, cfg.max));
    setMode(m);
  };

  const result = useMemo<{
    total?: number;
    profit?: number;
    principal?: number;
    first?: number;
    last?: number;
    totalPaid?: number;
    overpay?: number;
    varies?: boolean;
  }>(() => {
    if (mode === "deposit") {
      const profit = amount * (rate / 100) * (months / 12);
      return { total: amount + profit, profit };
    }
    const principal = mode === "mortgage" ? Math.max(0, price - down) : amount;
    return loanResult(principal, rate, months, method);
  }, [mode, amount, price, down, rate, months, method]);

  const numField = (
    label: string,
    value: number,
    setValue: (v: number) => void,
    cfg: FieldConfig,
    suffix?: string,
    decimals?: boolean
  ) => (
    <NumField
      label={label}
      value={value}
      onChange={setValue}
      cfg={cfg}
      suffix={suffix}
      decimals={decimals}
      tk={tk}
      cardBg={cardBg}
      accent={accent}
    />
  );

  const tabs: { id: Mode; label: string }[] = [
    { id: "credit", label: s.calcTabCredit },
    { id: "mortgage", label: s.calcTabMortgage },
    { id: "deposit", label: s.calcTabDeposit },
  ];

  return createPortal(
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
          {tabs.map((t) => {
            const active = mode === t.id;
            return (
              <button
                key={t.id}
                className={styles.tab}
                onClick={() => switchMode(t.id)}
                style={{
                  background: active ? tk.card : "transparent",
                  color: active ? accent : tk.muted,
                  boxShadow: active ? "0 2px 8px rgba(9,20,34,.14)" : "none",
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        {isLoan && (
          <div className={styles.methodRow}>
            <span className={styles.methodLabel} style={{ color: tk.muted }}>{s.calcMethod}</span>
            <div className={styles.methodTabs} style={{ background: cardBg }}>
              {([
                { id: "flat", label: s.calcMethodFlat },
                { id: "annuity", label: s.calcMethodAnnuity },
                { id: "diff", label: s.calcMethodDiff },
              ] as { id: PayMethod; label: string }[]).map((mt) => {
                const active = method === mt.id;
                return (
                  <button
                    key={mt.id}
                    className={styles.methodTab}
                    onClick={() => setMethod(mt.id)}
                    style={{
                      background: active ? accent : "transparent",
                      color: active ? "#fff" : tk.muted,
                    }}
                  >
                    {mt.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className={styles.fields} key={mode}>
          {mode === "credit" && numField(s.calcCreditAmount, amount, setAmount, AMOUNT, cur)}
          {mode === "deposit" && numField(s.calcDepositAmount, amount, setAmount, AMOUNT, cur)}
          {mode === "mortgage" && (
            <>
              {numField(s.calcPrice, price, setPrice, PRICE, cur)}
              {numField(s.calcDownPayment, down, setDown, { min: 0, max: price, step: 100_000 }, cur)}
            </>
          )}
          {numField(s.calcRate, rate, setRate, RATE, "%", true)}
          {numField(s.calcMonths, months, setMonths, monthsCfg, s.calcUnitMonths)}
        </div>

        <div className={styles.results} style={{ background: cardBg }} key={`res-${mode}`}>
          {mode === "deposit" ? (
            <>
              <div className={styles.resultMain}>
                <span className={styles.resultMainLabel} style={{ color: tk.muted }}>{s.calcTotal}</span>
                <span className={styles.resultMainValue} style={{ color: accent }}>
                  {groupNum(result.total ?? 0)} {cur}
                </span>
              </div>
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcProfit}</span>
                <span className={styles.resultRowValue} style={{ color: "#2f9e6f" }}>
                  + {groupNum(result.profit ?? 0)} {cur}
                </span>
              </div>
            </>
          ) : (
            <>
              <div className={styles.resultMain}>
                <span className={styles.resultMainLabel} style={{ color: tk.muted }}>
                  {result.varies ? s.calcFirstMonth : s.calcMonthly}
                </span>
                <span className={styles.resultMainValue} style={{ color: accent }}>
                  {groupNum(result.first ?? 0)} {cur}
                </span>
              </div>
              {result.varies && (
                <div className={styles.resultRow} style={{ color: tk.muted }}>
                  <span>{s.calcLastMonth}</span>
                  <span className={styles.resultRowValue} style={{ color: tk.strong }}>
                    {groupNum(result.last ?? 0)} {cur}
                  </span>
                </div>
              )}
              {mode === "mortgage" && (
                <div className={styles.resultRow} style={{ color: tk.muted }}>
                  <span>{s.calcLoanAmount}</span>
                  <span className={styles.resultRowValue} style={{ color: tk.strong }}>
                    {groupNum(result.principal ?? 0)} {cur}
                  </span>
                </div>
              )}
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcTotalPaid}</span>
                <span className={styles.resultRowValue} style={{ color: tk.strong }}>
                  {groupNum(result.totalPaid ?? 0)} {cur}
                </span>
              </div>
              <div className={styles.resultRow} style={{ color: tk.muted }}>
                <span>{s.calcOverpay}</span>
                <span className={styles.resultRowValue} style={{ color: ACCENT }}>
                  {groupNum(result.overpay ?? 0)} {cur}
                </span>
              </div>
            </>
          )}
        </div>

        <div className={styles.note} style={{ color: tk.muted }}>{s.calcNote}</div>
      </div>
    </div>,
    document.body
  );
}
