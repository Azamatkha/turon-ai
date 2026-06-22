import { ReactNode } from "react";
import styles from "./StatCard.module.css";

export interface StatDef {
  icon: ReactNode;
  value: string;
  label: string;
  trend: string;
  tint: string;
}

export default function StatCard({ icon, value, label, trend, tint }: StatDef) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div className={styles.iconWrap} style={{ background: tint + "14", color: tint }}>{icon}</div>
        <div className={styles.trend}>{trend}</div>
      </div>
      <div className={styles.value}>{value}</div>
      <div className={styles.label}>{label}</div>
    </div>
  );
}
