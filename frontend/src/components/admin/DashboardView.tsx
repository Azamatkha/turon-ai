import { useEffect, useState } from "react";
import StatCard, { StatDef } from "./StatCard";
import WeeklyChart from "./WeeklyChart";
import DepartmentBreakdown from "./DepartmentBreakdown";
import RecentActivity from "./RecentActivity";
import { getStats, type DashboardStats } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./DashboardView.module.css";

// ISO vaqtni "5 daq oldin" ko'rinishida
function relTime(iso: string, admin: AdminStrings): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.round(diff / 60000);
  if (m < 1) return admin.timeNow;
  if (m < 60) return admin.timeMinAgo(m);
  const h = Math.round(m / 60);
  if (h < 24) return admin.timeHourAgo(h);
  return admin.timeDayAgo(Math.round(h / 24));
}

// Bo'limlar progress-bar ranglari (aylanib ishlatiladi)
const DEPT_COLORS = ["#2a6f97", "#3a7ca5", "#5b8fb0", "#7fb3d2", "#9bc1d9", "#6fa8c9"];

const usersIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
const chatIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" /></svg>;
const msgIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
const onlineIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.4" fill="currentColor" stroke="none" /></svg>;
const likeIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12" /><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" /></svg>;
const dislikeIcon = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2" /><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" /></svg>;

export default function DashboardView({ mounted, t: admin }: { mounted: boolean; t: AdminStrings }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(null));
  }, []);

  const fmt = (n: number) => n.toLocaleString();

  // So'nggi faollik amali -> matn + rang
  const ACTIVITY: Record<string, { text: string; c: string }> = {
    login: { text: admin.actLogin, c: "#1f8a5b" },
    logout: { text: admin.actLogout, c: "#c0392b" },
    session: { text: admin.actSession, c: "#3a7ca5" },
    message: { text: admin.actMessage, c: "#5b8fb0" },
  };

  const statDefs: StatDef[] = [
    { icon: usersIcon, value: stats ? fmt(stats.total_users) : "—", label: admin.statTotalUsers, trend: "", tint: "#2a6f97" },
    { icon: chatIcon, value: stats ? fmt(stats.total_sessions) : "—", label: admin.statTotalSessions, trend: "", tint: "#3a7ca5" },
    { icon: msgIcon, value: stats ? fmt(stats.total_messages) : "—", label: admin.statTotalMessages, trend: "", tint: "#5b8fb0" },
    { icon: onlineIcon, value: stats ? fmt(stats.online) : "—", label: admin.statOnline, trend: "", tint: "#1f8a5b" },
    { icon: likeIcon, value: stats ? fmt(stats.total_likes) : "—", label: admin.statLikes, trend: "", tint: "#1f8a5b" },
    { icon: dislikeIcon, value: stats ? fmt(stats.total_dislikes) : "—", label: admin.statDislikes, trend: "", tint: "#c0392b" },
  ];

  const deptDefs = (stats?.departments ?? []).map((d, i) => ({
    name: d.name,
    pct: d.pct,
    c: DEPT_COLORS[i % DEPT_COLORS.length],
  }));

  const barData = (stats?.weekly ?? []).map((w) => ({ day: w.label, value: w.count }));
  const barMax = Math.max(1, ...barData.map((b) => b.value));

  const activity = (stats?.recent_activity ?? []).map((a) => {
    const info = ACTIVITY[a.action] ?? { text: a.action, c: "#9aafb8" };
    return { who: a.name, what: info.text, when: relTime(a.when, admin), c: info.c };
  });

  return (
    <div className={styles.dashboard}>
      <div className={styles.statGrid}>
        {statDefs.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.chartRow}>
        <WeeklyChart data={barData} max={barMax} mounted={mounted} t={admin} />
        <DepartmentBreakdown departments={deptDefs} mounted={mounted} t={admin} />
      </div>

      {activity.length > 0 && <RecentActivity items={activity} t={admin} />}
    </div>
  );
}
