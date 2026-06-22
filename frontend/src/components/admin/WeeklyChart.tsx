import { admin } from "../../locales";
import styles from "./WeeklyChart.module.css";

interface DayValue {
  day: string;
  value: number;
}

interface WeeklyChartProps {
  data: DayValue[];
  max: number;
  mounted: boolean;
}

export default function WeeklyChart({ data, max, mounted }: WeeklyChartProps) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div>
          <div className={styles.title}>{admin.weeklyMessagesTitle}</div>
          <div className={styles.sub}>{admin.weeklyMessagesSub}</div>
        </div>
        <div className={styles.totalRow}>
          <span className={styles.total}>18.4k</span>
          <span className={styles.totalTrend}>+12%</span>
        </div>
      </div>
      <div className={styles.bars}>
        {data.map((b, i) => (
          <div key={b.day} className={styles.barCol}>
            <div
              title={b.value.toLocaleString()}
              className={`${styles.bar} ${i === 3 ? styles.barHighlight : styles.barNormal}`}
              style={{ height: mounted ? (b.value / max) * 100 + "%" : "0%", transitionDelay: `${i * 0.07}s` }}
            />
            <span className={styles.dayLabel}>{b.day}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
