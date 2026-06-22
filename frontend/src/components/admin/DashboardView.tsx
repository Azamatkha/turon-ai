import StatCard, { StatDef } from "./StatCard";
import WeeklyChart from "./WeeklyChart";
import DepartmentBreakdown from "./DepartmentBreakdown";
import RecentActivity from "./RecentActivity";
import styles from "./DashboardView.module.css";

const statDefs: StatDef[] = [
  { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>, value: "1,284", label: "Jami foydalanuvchilar", trend: "+38", tint: "#2a6f97" },
  { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" /></svg>, value: "312", label: "Bugungi faol suhbatlar", trend: "+9%", tint: "#3a7ca5" },
  { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>, value: "2,640", label: "Kunlik xabarlar", trend: "+12%", tint: "#173f73" },
  { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></svg>, value: "1.8s", label: "O‘rtacha javob", trend: "−0.3s", tint: "#3a7ca5" },
];

const barData = [
  { day: "Du", value: 2100 }, { day: "Se", value: 2600 }, { day: "Ch", value: 2300 },
  { day: "Pa", value: 3100 }, { day: "Ju", value: 2800 }, { day: "Sh", value: 1500 }, { day: "Ya", value: 1200 },
];
const max = 3200;

const deptDefs = [
  { name: "Chakana banking", pct: 42, c: "#2a6f97" },
  { name: "Korporativ", pct: 27, c: "#3a7ca5" },
  { name: "Komplayens", pct: 19, c: "#173f73" },
  { name: "G‘aznachilik", pct: 12, c: "#7fb3d2" },
];

const activity = [
  { who: "Sevara Rahimova", what: "karta nizosini hal qildi", when: "2 daq oldin", c: "#1f8a5b" },
  { who: "Bobur Aliyev", what: "ish maydoniga taklif qilindi", when: "24 daq oldin", c: "#3a7ca5" },
  { who: "Jasur Komilov", what: "AML ro‘yxatini yaratdi", when: "1 soat oldin", c: "#2a6f97" },
  { who: "Nigora Usmonova", what: "akkaunti to‘xtatildi", when: "3 soat oldin", c: "#c0392b" },
];

export default function DashboardView({ mounted }: { mounted: boolean }) {
  return (
    <div className={styles.dashboard}>
      <div className={styles.statGrid}>
        {statDefs.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.chartRow}>
        <WeeklyChart data={barData} max={max} mounted={mounted} />
        <DepartmentBreakdown departments={deptDefs} mounted={mounted} />
      </div>

      <RecentActivity items={activity} />
    </div>
  );
}
