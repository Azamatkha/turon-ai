import { ReactNode } from "react";
import styles from "./StatCard.module.css";

export interface StatDef {
  icon: ReactNode;
  value: string;
  label: string;
  trend: string;
  tint: string;      // ikonka rangi (CSS o'zgaruvchi — mavzuga moslashadi)
  tintBg: string;    // ikonka foni (alohida: CSS o'zgaruvchiga "14" qo'shib bo'lmaydi)
}

export default function StatCard({ icon, value, label, trend, tint, tintBg }: StatDef) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div className={styles.iconWrap} style={{ background: tintBg, color: tint }}>{icon}</div>
        {trend && <div className={styles.trend}>{trend}</div>}
      </div>
      <div className={styles.value}>{value}</div>
      <div className={styles.label}>{label}</div>
    </div>
  );
}
