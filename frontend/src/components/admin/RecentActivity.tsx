import { admin } from "../../locales";
import styles from "./RecentActivity.module.css";

interface ActivityItem {
  who: string;
  what: string;
  when: string;
  c: string;
}

export default function RecentActivity({ items }: { items: ActivityItem[] }) {
  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.recentActivityTitle}</div>
      <div className={styles.list}>
        {items.map((a, i) => (
          <div key={i} className={styles.row}>
            <div className={styles.dot} style={{ background: a.c, boxShadow: `0 0 0 3px ${a.c}22` }} />
            <span className={styles.text}><span className={styles.who}>{a.who}</span> {a.what}</span>
            <span className={styles.when}>{a.when}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
