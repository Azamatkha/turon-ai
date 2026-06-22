import { useState, ReactNode } from "react";
import type { AdminUser, AdminRole, AdminStatus } from "../../types/admin";
import { admin } from "../../locales";
import styles from "./UsersTable.module.css";

const roleColor: Record<AdminRole, string> = { Admin: "#173f73", Manager: "#2a6f97", Agent: "#3a7ca5" };
const statusColor: Record<AdminStatus, string> = { Active: "#1f8a5b", Invited: "#b8860b", Suspended: "#c0392b" };

// Hoverlanadigan jadval qatori
function HoverRow({ children, last, index }: { children: ReactNode; last: boolean; index: number }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`${styles.row} ${last ? "" : styles.rowBorder} ${hovered ? styles.rowHover : styles.rowIdle}`}
      style={{ animationDelay: `${index * 0.04}s` }}
    >
      {children}
    </div>
  );
}

export default function UsersTable({ users, search }: { users: AdminUser[]; search: string }) {
  return (
    <div className={styles.table}>
      <div className={styles.headRow}>
        <span>{admin.tableUser}</span><span>{admin.tableDept}</span><span>{admin.tableRole}</span><span>{admin.tableStatus}</span><span />
      </div>
      {users.map((u, i) => (
        <HoverRow key={u.id} last={i === users.length - 1} index={i}>
          <div className={styles.userCell}>
            <div className={styles.avatar}>{u.name.charAt(0).toUpperCase()}</div>
            <div>
              <div className={styles.userName}>{u.name}</div>
              <div className={styles.userHandle}>{u.handle}</div>
            </div>
          </div>
          <span className={styles.deptCell}>{u.dept}</span>
          <span className={styles.cellCenter}><span className={styles.rolePill} style={{ color: roleColor[u.role], background: roleColor[u.role] + "16" }}>{admin.roleLabel[u.role]}</span></span>
          <span className={styles.cellCenter}><span className={styles.statusPill} style={{ color: statusColor[u.status], background: statusColor[u.status] + "14" }}><span className={styles.statusDot} style={{ background: statusColor[u.status] }} />{admin.statusLabel[u.status]}</span></span>
          <button title={admin.more} className={styles.moreBtn}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></svg>
          </button>
        </HoverRow>
      ))}
      {users.length === 0 && <div className={styles.empty}>{admin.noUsersFound(search)}</div>}
    </div>
  );
}
