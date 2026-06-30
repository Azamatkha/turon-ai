import { useState } from "react";
import type { AdminUser, AdminRole, AdminStatus } from "../../types/admin";
import { admin } from "../../locales";
import EditUserModal from "./EditUserModal";
import styles from "./UsersTable.module.css";

const roleColor: Record<AdminRole, string> = { Admin: "#173f73", Xodim: "#3a7ca5" };
const statusColor: Record<AdminStatus, string> = { Active: "#1f8a5b", Suspended: "#c0392b" };

interface Props {
  users: AdminUser[];
  search: string;
  onChangeRole: (id: string, role: AdminRole) => void;
  onDelete: (id: string) => void;
  onUpdate: (id: string, input: { username?: string; full_name?: string; department?: string; password?: string }) => Promise<void>;
}

// Hoverlanadigan jadval qatori + amallar menyusi (tahrirlash / rol / o'chirish)
function HoverRow({ user, last, index, onChangeRole, onDelete, onEdit }: {
  user: AdminUser; last: boolean; index: number;
  onChangeRole: (id: string, role: AdminRole) => void;
  onDelete: (id: string) => void;
  onEdit: (u: AdminUser) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const [menu, setMenu] = useState(false);
  const u = user;
  const nextRole: AdminRole = u.role === "Admin" ? "Xodim" : "Admin";
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setMenu(false); }}
      className={`${styles.row} ${last ? "" : styles.rowBorder} ${hovered ? styles.rowHover : styles.rowIdle}`}
      style={{ animationDelay: `${index * 0.04}s`, position: "relative" }}
    >
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
      <button title={admin.more} className={styles.moreBtn} onClick={() => setMenu((m) => !m)}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></svg>
      </button>

      {menu && (
        <div style={{ position: "absolute", right: 12, ...(last ? { bottom: 46 } : { top: 46 }), zIndex: 20, background: "#fff", border: "1px solid #e6eae3", borderRadius: 12, boxShadow: "0 16px 40px rgba(13,33,45,.18)", padding: 6, minWidth: 190 }}> 
          <button onClick={() => { onEdit(u); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "#173f73", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" /></svg>
            {admin.editUser}
          </button>
          <button onClick={() => { onChangeRole(u.id, nextRole); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "#173f73", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6M22 11h-6" /></svg>
            {u.role === "Admin" ? admin.makeXodim : admin.makeAdmin}
          </button>
          <div style={{ height: 1, background: "#eef1ec", margin: "6px 4px" }} />
          <button onClick={() => { onDelete(u.id); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "#c0392b", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /></svg>
            {admin.delete}
          </button>
        </div>
      )}
    </div>
  );
}

export default function UsersTable({ users, search, onChangeRole, onDelete, onUpdate }: Props) {
  const [editing, setEditing] = useState<AdminUser | null>(null);
  return (
    <div className={styles.table}>
      <div className={styles.headRow}>
        <span>{admin.tableUser}</span><span>{admin.tableDept}</span><span>{admin.tableRole}</span><span>{admin.tableStatus}</span><span />
      </div>
      {users.map((u, i) => (
        <HoverRow key={u.id} user={u} last={i === users.length - 1} index={i} onChangeRole={onChangeRole} onDelete={onDelete} onEdit={setEditing} />
      ))}
      {users.length === 0 && <div className={styles.empty}>{admin.noUsersFound(search)}</div>}

      {editing && (
        <EditUserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSubmit={(input) => onUpdate(editing.id, input)}
        />
      )}
    </div>
  );
}
