import type { AdminStrings } from "../../types/i18n";
import styles from "./RecentActivity.module.css";

interface ActivityItem {
  who: string;
  what: string;
  when: string;
  c: string;    // nuqta rangi (CSS o'zgaruvchi)
  bg: string;   // nuqta atrofidagi halqa foni (alohida — var'ga "22" qo'shib bo'lmaydi)
}

export default function RecentActivity({ items, t: admin }: { items: ActivityItem[]; t: AdminStrings }) {
  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.recentActivityTitle}</div>
      <div className={styles.list}>
        {items.map((a, i) => (
          <div key={i} className={styles.row}>
            <div className={styles.dot} style={{ background: a.c, boxShadow: `0 0 0 3px ${a.bg}` }} />
            <span className={styles.text}><span className={styles.who}>{a.who}</span> {a.what}</span>
            <span className={styles.when}>{a.when}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
