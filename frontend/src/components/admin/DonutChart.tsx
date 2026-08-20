import styles from "./DonutChart.module.css";

export interface DonutSlice {
  label: string;
  /** Xom qiymat (foiz emas) — ulush shu yerda hisoblanadi */
  value: number;
  /** CSS rangi, odatda `var(--chart-N)` */
  color: string;
}

interface DonutChartProps {
  slices: DonutSlice[];
  mounted: boolean;
  /** Halqa markazidagi katta son (masalan "87%") — bo'sh bo'lsa markaz bo'sh qoladi */
  centerValue?: string;
  centerLabel?: string;
  /** Ekran o'quvchisi uchun umumiy tavsif */
  ariaLabel: string;
  /** Ulush yonida ko'rsatiladigan qiymatni formatlash (sukut bo'yicha foiz) */
  formatValue?: (slice: DonutSlice, pct: number) => string;
}

// SVG geometriyasi. Radius va qalinlik viewBox birligida (piksel emas) —
// karta kengligi o'zgarsa halqa o'zi masshtablanadi.
const R = 46;
const STROKE = 17;
const C = 2 * Math.PI * R;

// Bo'laklar orasidagi tirqish. Rangdan rangga to'g'ridan-to'g'ri o'tish
// chegarani yo'qotadi — ayniqsa yonma-yon ikki yaqin tus tushganda. Tirqish
// karta foni rangida emas, shunchaki chizilmagan joy: ostidagi "track"
// halqasi ko'rinadi.
const GAP = 2;

export default function DonutChart({
  slices, mounted, centerValue, centerLabel, ariaLabel, formatValue,
}: DonutChartProps) {
  const total = slices.reduce((s, x) => s + x.value, 0);

  // Jami 0 bo'lsa bo'linish NaN beradi va halqa umuman chizilmaydi —
  // shu holatni chaqiruvchi komponent hal qiladi (bo'sh holat matni).
  if (total <= 0) return null;

  // Har bir bo'lakning boshlanish nuqtasi (yig'indi ulush).
  let acc = 0;
  const arcs = slices.map((s) => {
    const pct = (s.value / total) * 100;
    const len = (s.value / total) * C;
    const offset = acc;
    acc += len;
    return { ...s, pct, len, offset };
  });

  return (
    <div className={styles.wrap}>
      <div className={styles.ringBox}>
        <svg viewBox="0 0 120 120" className={styles.svg} role="img" aria-label={ariaLabel}>
          {/* Ostki halqa — bo'laklar orasidagi tirqishlar shu yerda ko'rinadi,
              shuning uchun halqa uzuq emas, bir butun bo'lib o'qiladi. */}
          <circle cx="60" cy="60" r={R} fill="none" stroke="var(--chart-grid)" strokeWidth={STROKE} />
          {arcs.map((a) => (
            <circle
              key={a.label}
              cx="60"
              cy="60"
              r={R}
              fill="none"
              stroke={a.color}
              strokeWidth={STROKE}
              // Bitta aylanadan bo'lak yasash: ko'rinadigan uzunlik + qolgani
              // bo'sh. Tirqish uchun uzunlikdan GAP ayiriladi (juda kichik
              // bo'lakda manfiy chiqmasligi uchun 0 dan pasaymaydi).
              strokeDasharray={`${Math.max(0, (mounted ? a.len : 0) - GAP)} ${C}`}
              strokeDashoffset={-a.offset}
              // Boshlanish nuqtasi soat 12 da bo'lsin (SVG'da sukut bo'yicha
              // soat 3 dan boshlanadi).
              transform="rotate(-90 60 60)"
              className={styles.arc}
            >
              <title>{`${a.label}: ${a.value.toLocaleString()} (${a.pct.toFixed(1)}%)`}</title>
            </circle>
          ))}
        </svg>
        {centerValue && (
          <div className={styles.center}>
            <div className={styles.centerValue}>{centerValue}</div>
            {centerLabel && <div className={styles.centerLabel}>{centerLabel}</div>}
          </div>
        )}
      </div>

      {/* Izoh ro'yxati — rang YOLG'IZ belgilovchi bo'lib qolmasligi uchun
          majburiy: har bo'lak nomi va qiymati matn bilan ham yozilgan. */}
      <ul className={styles.legend}>
        {arcs.map((a) => (
          <li key={a.label} className={styles.legendRow}>
            <span className={styles.dot} style={{ background: a.color }} aria-hidden />
            <span className={styles.legendName} title={a.label}>{a.label}</span>
            <span className={styles.legendValue}>
              {formatValue ? formatValue(a, a.pct) : `${a.pct.toFixed(0)}%`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
