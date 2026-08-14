import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { FaCalculator } from "react-icons/fa6";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import {
  calcDeposit,
  calcLoan,
  fetchSchedule,
  type LoanInput,
  type PayMethod,
} from "../../services/calculatorService";
import {
  downloadSchedule,
  scheduleFileName,
  scheduleFromDto,
} from "../../utils/paymentSchedule";
import { ACCENT, PRIMARY, PRIMARY_ON_DARK } from "./theme";
import PaymentScheduleModal from "./PaymentScheduleModal";
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

// PayMethod umumiy modulda (services/calculatorService) — jadval so'rovi ham
// shu turdan foydalanadi, ikki joyda ikki xil bo'lib ketmasin.

// Slayder surilganda har piksel uchun so'rov yubormaslik uchun kutish vaqti.
// 260ms — barmoq/sichqoncha to'xtagani sezilarli, lekin foydalanuvchi
// "kechikish" deb his qilmaydigan oraliq.
const DEBOUNCE_MS = 260;

// Oddiy kredit: 6 oydan 60 oygacha (6 oy qadam). Ipoteka/avtokredit: 240 oygacha.
const MONTHS_CREDIT: FieldConfig = { min: 6, max: 60, step: 6 };
const MONTHS_MORTGAGE: FieldConfig = { min: 6, max: 240, step: 6 };
// Omonat: 1 oydan 60 oygacha.
const MONTHS_DEP: FieldConfig = { min: 1, max: 60, step: 1 };
// Foiz: 2 xonali kasr (21.99 kabi) — kiritishda erkin, slayder 0.1 qadam.
// Foiz: 2 xonali kasr (21.99). Oddiy kreditda eng past stavka 20% — bankda
// undan arzon iste'mol krediti yo'q. Ipoteka/avtokreditda (imtiyozli dasturlar)
// va omonatda bunday chegara qo'yilmaydi.
const RATE_CREDIT: FieldConfig = { min: 20, max: 50, step: 0.1 };
const RATE_OTHER: FieldConfig = { min: 0, max: 50, step: 0.1 };
// Oddiy kredit/omonat summasi: 100 mln gacha. Ipoteka narxi: 500 mln gacha.
const AMOUNT: FieldConfig = { min: 100_000, max: 100_000_000, step: 100_000 };
const PRICE: FieldConfig = { min: 1_000_000, max: 500_000_000, step: 1_000_000 };

// Raqamni bo'sh joy bilan guruhlaydi: 1234567 -> "1 234 567"
const groupNum = (n: number): string =>
  Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");

const clamp = (v: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, v));

// HISOB FORMULALARI BU YERDA EMAS — backendda (`src/calculator/services.py`,
// POST /v1/calculator/*). Ilgari shu faylda `loanResult()` turardi; bank
// shartlari o'zgarsa formulani front va backendda alohida yangilash kerak
// bo'lardi va ular farq qilib ketishi mumkin edi.

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
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [amount, setAmount] = useState(50_000_000);
  const [price, setPrice] = useState(300_000_000);
  const [down, setDown] = useState(60_000_000);
  const [rate, setRate] = useState(21.99);
  const [months, setMonths] = useState(24);

  const accent = isDark ? PRIMARY_ON_DARK : PRIMARY;
  const cardBg = "var(--tu-glass-bg-soft)";
  const monthsCfg =
    mode === "deposit" ? MONTHS_DEP : mode === "mortgage" ? MONTHS_MORTGAGE : MONTHS_CREDIT;
  // Oddiy kreditda eng past stavka 20%
  const rateCfg = mode === "credit" ? RATE_CREDIT : RATE_OTHER;
  const isLoan = mode === "credit" || mode === "mortgage";
  const cur = s.calcCurrency;

  // Rejim almashganda muddatni yangi qadamga/oraliqqa moslaymiz
  const switchMode = (m: Mode) => {
    if (m === mode) return;
    const cfg = m === "deposit" ? MONTHS_DEP : m === "mortgage" ? MONTHS_MORTGAGE : MONTHS_CREDIT;
    setMonths((v) => clamp(Math.round(v / cfg.step) * cfg.step || cfg.min, cfg.min, cfg.max));
    // Oddiy kreditga o'tilsa — stavka 20% dan past bo'lib qolmasin
    const rc = m === "credit" ? RATE_CREDIT : RATE_OTHER;
    setRate((v) => clamp(v, rc.min, rc.max));
    setMode(m);
  };

  // Kredit so'rovi tanasi. Ipotekada backend kredit tanasini o'zi hisoblaydi
  // (narx - boshlang'ich to'lov), shuning uchun ayirmani bu yerda qilmaymiz.
  const loanInput = useMemo<LoanInput>(
    () =>
      mode === "mortgage"
        ? { price, down_payment: down, rate, months, method }
        : { amount, rate, months, method },
    [mode, amount, price, down, rate, months, method]
  );

  // Natija endi serverdan keladi. Kutish paytida OLDINGI natija ekranda
  // qoladi (faqat xiralashadi) — aks holda har slayder harakatida raqamlar
  // yo'qolib-paydo bo'lib, "sakrab" ko'rinardi.
  const [result, setResult] = useState<{
    total?: number;
    profit?: number;
    principal?: number;
    first?: number;
    last?: number;
    totalPaid?: number;
    overpay?: number;
    varies?: boolean;
  }>({});
  const [pending, setPending] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    setPending(true);
    const timer = setTimeout(() => {
      const run = async () => {
        try {
          if (mode === "deposit") {
            const r = await calcDeposit({ amount, rate, months }, ctrl.signal);
            setResult({ total: r.total, profit: r.profit });
          } else {
            const r = await calcLoan(loanInput, ctrl.signal);
            setResult({
              principal: r.principal,
              first: r.first_payment,
              last: r.last_payment,
              totalPaid: r.total_paid,
              overpay: r.overpay,
              varies: r.varies,
            });
          }
          setFailed(false);
        } catch {
          // Bekor qilingan so'rov (yangi qiymat kiritildi) — xato emas
          if (!ctrl.signal.aborted) setFailed(true);
        } finally {
          if (!ctrl.signal.aborted) setPending(false);
        }
      };
      void run();
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [mode, amount, rate, months, loanInput]);

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

  // Jadvalni ko'rmasdan to'g'ridan-to'g'ri Excel'ga yuklash. Qatorlar
  // backenddan olinadi, Excel fayl esa brauzerda yig'iladi (server fayl
  // yaratmaydi — yuklama va vaqtinchalik fayllar bilan ovora bo'lmaydi).
  const [dlBusy, setDlBusy] = useState(false);
  const downloadXls = async () => {
    if (dlBusy) return;
    setDlBusy(true);
    try {
      const dto = await fetchSchedule(loanInput);
      downloadSchedule(
        scheduleFromDto(dto),
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
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setDlBusy(false);
    }
  };

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
        <div className={styles.scroll}>
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
                  boxShadow: active ? "0 2px 8px rgba(15,23,42,.14)" : "none",
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
          {numField(s.calcRate, rate, setRate, rateCfg, "%", true)}
          {numField(s.calcMonths, months, setMonths, monthsCfg, s.calcUnitMonths)}
        </div>

        {/* Server javobi kutilayotganda natija butunlay yo'qolmaydi — biroz
            xiralashadi. Shunda slayder surilganda raqamlar "sakramaydi". */}
        <div
          className={styles.results}
          style={{ background: cardBg, opacity: pending ? 0.55 : 1, transition: "opacity .15s ease" }}
          aria-busy={pending}
          key={`res-${mode}`}
        >
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
                <span className={styles.resultRowValue} style={{ color: "#059669" }}>
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
                <span className={styles.resultRowValue} style={{ color: accent }}>
                  {groupNum(result.overpay ?? 0)} {cur}
                </span>
              </div>
            </>
          )}
        </div>

        {isLoan && (
          <div className={styles.scheduleRow}>
            <button
              className={styles.scheduleBtn}
              style={{ color: accent, borderColor: accent }}
              onClick={() => setScheduleOpen(true)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="3" y1="10" x2="21" y2="10" /><line x1="9" y1="4" x2="9" y2="22" /></svg>
              {s.calcScheduleView}
            </button>
            <button
              className={styles.scheduleBtnFill}
              style={{ background: accent, opacity: dlBusy ? 0.6 : 1 }}
              disabled={dlBusy}
              onClick={() => void downloadXls()}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
              {s.calcScheduleDownload}
            </button>
          </div>
        )}

        {failed && (
          <div className={styles.note} style={{ color: "#DC2626" }} role="alert">{s.calcError}</div>
        )}
        <div className={styles.note} style={{ color: tk.muted }}>{s.calcNote}</div>
        </div>
      </div>

      {scheduleOpen && isLoan && (
        <PaymentScheduleModal
          input={loanInput}
          tk={tk}
          isDark={isDark}
          s={s}
          onClose={() => setScheduleOpen(false)}
        />
      )}
    </div>,
    document.body
  );
}
