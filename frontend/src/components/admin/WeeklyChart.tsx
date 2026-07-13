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

export default function WeeklyChart({ data, max, mounted, t: admin }: WeeklyChartProps) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div>
          <div className={styles.title}>{admin.weeklyMessagesTitle}</div>
          <div className={styles.sub}>{admin.weeklyMessagesSub}</div>
        </div>
        <div className={styles.totalRow}>
          <span className={styles.total}>{data.reduce((s, b) => s + b.value, 0).toLocaleString()}</span>
        </div>
      </div>
      <div className={styles.bars}>
        {data.map((b, i) => (
          <div key={b.day} className={styles.barCol}>
            <div
              data-tip={b.value.toLocaleString()}
              className={`${styles.bar} ${b.value === max && max > 0 ? styles.barHighlight : styles.barNormal}`}
              style={{ height: mounted ? (b.value / max) * 100 + "%" : "0%", transitionDelay: `${i * 0.07}s` }}
            />
            <span className={styles.dayLabel}>{b.day}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
