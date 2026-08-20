import type { AdminStrings } from "../../types/i18n";
import styles from "./WeeklyChart.module.css";

interface DayValue {
  day: string;
  value: number;
}

interface WeeklyChartProps {
  data: DayValue[];
  max: number;
  mounted: boolean;
  t: AdminStrings;
}

// Gorizontal to'r chiziqlari nechta bo'lakka bo'lsin. 4 — o'qishga yetarli,
// ko'proq chiziq grafikni "katakli daftar"ga aylantiradi.
const GRID_STEPS = 4;

export default function WeeklyChart({ data, max, mounted, t: admin }: WeeklyChartProps) {
  const total = data.reduce((s, b) => s + b.value, 0);
  const avg = data.length > 0 ? total / data.length : 0;
  // O'rtacha chizig'i eng baland ustundan yuqori chiqmaydi (max >= avg doim),
  // lekin max=0 bo'lsa bo'linish NaN beradi.
  const avgPct = max > 0 ? (avg / max) * 100 : 0;

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div>
          <div className={styles.title}>{admin.weeklyMessagesTitle}</div>
          <div className={styles.sub}>{admin.weeklyMessagesSub}</div>
        </div>
        <div className={styles.totalRow}>
          <span className={styles.total}>{total.toLocaleString()}</span>
          {/* O'rtacha qiymat SARLAVHADA yoziladi, chizma ustida emas.
              Uzuq chiziqning yoniga yorliq qo'yilsa u eng chap ustun ustiga
              tushib, shisha fonda o'qilmay qolardi. */}
          {max > 0 && (
            <span className={styles.avgValue}>
              {admin.weeklyAvg} {Math.round(avg).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      <div className={styles.plot}>
        {/* To'r chiziqlari + qiymat belgilari. Ilgari grafikda o'q umuman
            yo'q edi: ustun balandligini faqat bir-biriga nisbatan ko'rish
            mumkin edi, "bu qancha?" degan savolga esa faqat hover javob
            berardi. Endi shkala ko'rinib turadi. */}
        <div className={styles.grid} aria-hidden>
          {Array.from({ length: GRID_STEPS + 1 }, (_, i) => {
            const frac = 1 - i / GRID_STEPS;
            return (
              <div key={frac} className={styles.gridLine}>
                <span className={styles.gridLabel}>{Math.round(max * frac).toLocaleString()}</span>
              </div>
            );
          })}
        </div>

        {/* O'rtacha chizig'i — kunlar orasidagi farqni "ko'p/kam" emas,
            "o'rtachadan yuqori/past" deb o'qish imkonini beradi. Qiymati
            sarlavhada yozilgani uchun chiziqning o'zi yorliqsiz. */}
        {max > 0 && (
          <div className={styles.avgLine} style={{ bottom: `${avgPct}%` }} aria-hidden />
        )}

        <div className={styles.bars}>
          {data.map((b, i) => (
            <div key={b.day} className={styles.barCol}>
              <div
                data-tip={b.value.toLocaleString()}
                className={`${styles.bar} ${b.value === max && max > 0 ? styles.barHighlight : styles.barNormal}`}
                style={{ height: mounted ? (b.value / max) * 100 + "%" : "0%", transitionDelay: `${i * 0.07}s` }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Kun yorliqlari chizma MAYDONIDAN TASHQARIDA. Ilgari ular ustun
          bilan bitta ustunda edi va to'r chiziqlari qo'shilganda ular ham
          shkala ichiga tushib qolardi. */}
      <div className={styles.dayRow}>
        {data.map((b) => (
          <span key={b.day} className={styles.dayLabel}>{b.day}</span>
        ))}
      </div>
    </div>
  );
}
