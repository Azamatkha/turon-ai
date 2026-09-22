import DonutChart, { type DonutSlice } from "./DonutChart";
import type { AdminStrings } from "../../types/i18n";
import styles from "./FeedbackDonut.module.css";

interface FeedbackDonutProps {
  likes: number;
  dislikes: number;
  /** Jami savollar (≈ bot javoblari soni) — necha foiz javob baholanganini hisoblash uchun */
  totalAnswers: number;
  mounted: boolean;
  t: AdminStrings;
}

export default function FeedbackDonut({ likes, dislikes, totalAnswers, mounted, t: admin }: FeedbackDonutProps) {
  const total = likes + dislikes;

  // RANG BU YERDA TOIFA EMAS, HOLAT. Shuning uchun --chart-* toifa ranglari
  // emas, holat ranglari (success/danger) ishlatiladi: "yoqdi" yaxshi,
  // "yoqmadi" yomon degan ma'noni rang o'zi tashiydi. Toifa ranglarini bu
  // yerga qo'yish ularning ma'nosini buzardi.
  const slices: DonutSlice[] = [
    { label: admin.feedbackLikes, value: likes, color: "var(--adm-success)" },
    { label: admin.feedbackDislikes, value: dislikes, color: "var(--adm-danger)" },
  ];

  const satisfaction = total > 0 ? Math.round((likes / total) * 100) : 0;
  // Baholangan javoblar ulushi — 100% dan oshmaydi (eski ma'lumotlarda
  // xabar o'chirilgan bo'lsa ham)
  const coverage = totalAnswers > 0 ? Math.min(100, Math.round((total / totalAnswers) * 100)) : 0;

  // ILGARI halqa yonida faqat ikki qator izoh turardi va karta o'ng tomoni
  // bo'sh qolardi. Endi har baho — son + ulush ustuni, pastda esa umumiy
  // ko'rsatkichlar: kartadagi joy ma'lumot bilan to'ladi.
  const legend = (
    <div className={styles.side}>
      {slices.map((s, i) => {
        const pct = total > 0 ? (s.value / total) * 100 : 0;
        return (
          <div key={s.label} className={styles.stat}>
            <div className={styles.statTop}>
              <span className={styles.dot} style={{ background: s.color }} aria-hidden />
              <span className={styles.statName}>{s.label}</span>
              <span className={styles.statValue}>{s.value.toLocaleString()}</span>
              <span className={styles.statPct}>{Math.round(pct)}%</span>
            </div>
            <div className={styles.track}>
              <div
                className={styles.bar}
                style={{ background: s.color, width: mounted ? `${pct}%` : "0%", transitionDelay: `${i * 0.08}s` }}
              />
            </div>
          </div>
        );
      })}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaValue}>{total.toLocaleString()}</span>
          <span className={styles.metaLabel}>{admin.feedbackTotal}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaValue}>{coverage}%</span>
          <span className={styles.metaLabel}>{admin.feedbackCoverage}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.feedbackTitle}</div>
      <div className={styles.sub}>{admin.feedbackSub}</div>
      {total === 0 ? (
        <div className={styles.empty}>{admin.chartNoData}</div>
      ) : (
        <DonutChart
          slices={slices}
          mounted={mounted}
          centerValue={`${satisfaction}%`}
          centerLabel={admin.feedbackSatisfaction}
          ariaLabel={admin.feedbackTitle}
          legend={legend}
        />
      )}
    </div>
  );
}
