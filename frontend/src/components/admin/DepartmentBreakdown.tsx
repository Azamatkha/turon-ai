import { admin } from "../../locales";
import styles from "./DepartmentBreakdown.module.css";

interface DeptDef {
  name: string;
  pct: number;
  c: string;
}

interface DepartmentBreakdownProps {
  departments: DeptDef[];
  mounted: boolean;
}

export default function DepartmentBreakdown({ departments, mounted }: DepartmentBreakdownProps) {
  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.deptUsageTitle}</div>
      <div className={styles.sub}>{admin.deptUsageSub}</div>
      <div className={styles.list}>
        {departments.map((d, i) => (
          <div key={d.name}>
            <div className={styles.row}>
              <span className={styles.deptName}>{d.name}</span>
              <span className={styles.deptPct}>{d.pct}%</span>
            </div>
            <div className={styles.track}>
              <div className={styles.fill} style={{ background: d.c, width: mounted ? d.pct + "%" : "0%", transitionDelay: `${i * 0.08 + 0.2}s` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
