import { useEffect, useState } from "react";
import StatCard, { StatDef } from "./StatCard";
import WeeklyChart from "./WeeklyChart";
import DepartmentBreakdown from "./DepartmentBreakdown";
import RecentActivity from "./RecentActivity";
import { getStats, type DashboardStats } from "../../services/adminService";
import styles from "./DashboardView.module.css";

// ISO vaqtni "5 daq oldin" ko'rinishida
function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.round(diff / 60000);
  if (m < 1) return "hozir";
  if (m < 60) return `${m} daq oldin`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} soat oldin`;
  return `${Math.round(h / 24)} kun oldin`;
}

// Bo'limlar progress-bar ranglari (aylanib ishlatiladi)
const DEPT_COLORS = ["#2a6f97", "#3a7ca5", "#173f73", "#7fb3d2", "#5b8fb0", "#9bc1d9"];

const usersIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
const chatIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" /></svg>;
const msgIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
const deptIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /></svg>;

export default function DashboardView({ mounted }: { mounted: boolean }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(null));
  }, []);

  const fmt = (n: number) => n.toLocaleString();

  const statDefs: StatDef[] = [
    { icon: usersIcon, value: stats ? fmt(stats.total_users) : "—", label: "Jami foydalanuvchilar", trend: "", tint: "#2a6f97" },
    { icon: chatIcon, value: stats ? fmt(stats.total_sessions) : "—", label: "Jami suhbatlar", trend: "", tint: "#3a7ca5" },
    { icon: msgIcon, value: stats ? fmt(stats.total_messages) : "—", label: "Jami so‘rovlar", trend: "", tint: "#173f73" },
    { icon: deptIcon, value: stats ? fmt(stats.total_departments) : "—", label: "Bo‘limlar", trend: "", tint: "#3a7ca5" },
  ];

  const deptDefs = (stats?.departments ?? []).map((d, i) => ({
    name: d.name,
    pct: d.pct,
    c: DEPT_COLORS[i % DEPT_COLORS.length],
  }));

  const barData = (stats?.weekly ?? []).map((w) => ({ day: w.label, value: w.count }));
  const barMax = Math.max(1, ...barData.map((b) => b.value));

  const activity = (stats?.recent_activity ?? []).map((a) => ({
    who: a.name,
    what: "tizimga kirdi",
    when: relTime(a.when),
    c: "#1f8a5b",
  }));

  return (
    <div className={styles.dashboard}>
      <div className={styles.statGrid}>
        {statDefs.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.chartRow}>
        <WeeklyChart data={barData} max={barMax} mounted={mounted} />
        <DepartmentBreakdown departments={deptDefs} mounted={mounted} />
      </div>

      {activity.length > 0 && <RecentActivity items={activity} />}
    </div>
  );
}
