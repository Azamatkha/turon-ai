import DonutChart, { type DonutSlice } from "./DonutChart";
import type { AdminStrings } from "../../types/i18n";
import styles from "./FeedbackDonut.module.css";

interface FeedbackDonutProps {
  likes: number;
  dislikes: number;
  mounted: boolean;
  t: AdminStrings;
}

export default function FeedbackDonut({ likes, dislikes, mounted, t: admin }: FeedbackDonutProps) {
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
          // Bu yerda foiz emas, XOM SON ko'rsatiladi: markazdagi katta son
          // allaqachon foiz, izohda ham foiz berilsa bir xil ma'lumot ikki
          // marta yozilardi. Baho soni esa yangi ma'lumot.
          formatValue={(s) => s.value.toLocaleString()}
        />
      )}
    </div>
  );
}
