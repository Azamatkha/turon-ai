import DonutChart, { type DonutSlice } from "./DonutChart";
import type { AdminStrings } from "../../types/i18n";
import styles from "./DepartmentBreakdown.module.css";

export interface DeptDatum {
  name: string;
  count: number;
  pct: number;
}

interface DepartmentBreakdownProps {
  departments: DeptDatum[];
  mounted: boolean;
  t: AdminStrings;
}

// Tekshiruvdan o'tgan olti rang (index.css -> --chart-1..6). Ular AYLANIB
// ISHLATILMAYDI: yettinchi bo'lim uchun yangi tus o'ylab topilmaydi, chunki
// takrorlangan rang ikki xil bo'limni bir xil ko'rsatib qo'yardi. Oshiqchasi
// "Boshqalar" ga yig'iladi.
const SLOTS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"];

export default function DepartmentBreakdown({ departments, mounted, t: admin }: DepartmentBreakdownProps) {
  // Eng kattalari birinchi — halqa soat 12 dan boshlab kamayib boradi,
  // shunda eng muhim bo'lak ko'zga birinchi tushadi.
  const sorted = [...departments].sort((a, b) => b.count - a.count);
  const head = sorted.slice(0, SLOTS.length);
  const rest = sorted.slice(SLOTS.length);

  const slices: DonutSlice[] = head.map((d, i) => ({
    label: d.name,
    value: d.count,
    color: SLOTS[i],
  }));

  if (rest.length > 0) {
    slices.push({
      label: admin.chartOther,
      value: rest.reduce((s, d) => s + d.count, 0),
      color: "var(--chart-rest)",
    });
  }

  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.deptUsageTitle}</div>
      <div className={styles.sub}>{admin.deptUsageSub}</div>
      {slices.length === 0 ? (
        <div className={styles.empty}>{admin.chartNoData}</div>
      ) : (
        <DonutChart
          slices={slices}
          mounted={mounted}
          ariaLabel={admin.deptUsageTitle}
          formatValue={(s, pct) => `${pct.toFixed(0)}% · ${s.value.toLocaleString()}`}
        />
      )}
    </div>
  );
}
