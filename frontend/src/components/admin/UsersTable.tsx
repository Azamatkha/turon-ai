import { useState } from "react";
import type { AdminUser, AdminRole, AdminStatus } from "../../types/admin";
import type { AdminStrings } from "../../types/i18n";
import type { Lang } from "../../types/lang";
import { DEPARTMENTS, deptLabel } from "../../services/departments";
import EditUserModal from "./EditUserModal";
import styles from "./UsersTable.module.css";

// Backend'dan doim lotincha (`uz`) qiymat keladi — jadvalda joriy tilga mos
// nomni ko'rsatamiz. Ro'yxatda topilmasa (masalan eski/qo'lda kiritilgan
// qiymat) — borini shunday qoldiramiz.
function displayDept(dept: string, lang: Lang): string {
  const d = DEPARTMENTS.find((d) => d.uz === dept);
  return d ? deptLabel(d, lang) : dept;
}

// Ranglar CSS o'zgaruvchilaridan — dark mode'da avtomatik yorqinlashadi
// (avval hardcoded edi va qorong'u fonda o'qilmasdi).
const roleColor: Record<AdminRole, { c: string; bg: string }> = {
  Admin: { c: "var(--adm-info)", bg: "var(--adm-info-bg)" },
  Xodim: { c: "var(--adm-accent-2)", bg: "var(--adm-accent-2-bg)" },
};
const statusColor: Record<AdminStatus, { c: string; bg: string }> = {
  Active: { c: "var(--adm-success)", bg: "var(--adm-success-bg)" },
  Suspended: { c: "var(--adm-danger)", bg: "var(--adm-danger-bg)" },
};

interface Props {
  users: AdminUser[];
  search: string;
  onChangeRole: (id: string, role: AdminRole) => void;
  onDelete: (id: string) => void;
  onUpdate: (id: string, input: { username?: string; full_name?: string; department?: string; password?: string }) => Promise<void>;
  t: AdminStrings;
  lang: Lang;
}

// Hoverlanadigan jadval qatori + amallar menyusi (tahrirlash / rol / o'chirish)
function HoverRow({ user, last, index, onChangeRole, onDelete, onEdit, admin, lang }: {
  user: AdminUser; last: boolean; index: number;
  onChangeRole: (id: string, role: AdminRole) => void;
  onDelete: (id: string) => void;
  onEdit: (u: AdminUser) => void;
  admin: AdminStrings;
  lang: Lang;
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
      <span className={styles.deptCell}>{displayDept(u.dept, lang)}</span>
      <span className={styles.cellCenter}><span className={styles.rolePill} style={{ color: roleColor[u.role].c, background: roleColor[u.role].bg }}>{admin.roleLabel[u.role]}</span></span>
      <span className={styles.cellCenter}><span className={styles.statusPill} style={{ color: statusColor[u.status].c, background: statusColor[u.status].bg }}><span className={styles.statusDot} style={{ background: statusColor[u.status].c }} />{admin.statusLabel[u.status]}</span></span>
      <button data-tip={admin.more} aria-label={admin.more} className={styles.moreBtn} onClick={() => setMenu((m) => !m)}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></svg>
      </button>

      {menu && (
        <div style={{ position: "absolute", right: 12, ...(last ? { bottom: 46 } : { top: 46 }), zIndex: 20, background: "var(--adm-card)", border: "1px solid var(--adm-border)", borderRadius: 12, boxShadow: "0 16px 40px rgba(13,33,45,.18)", padding: 6, minWidth: 190 }}>
          <button onClick={() => { onEdit(u); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "var(--adm-text-strong)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z" /></svg>
            {admin.editUser}
          </button>
          <button onClick={() => { onChangeRole(u.id, nextRole); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "var(--adm-text-strong)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6M22 11h-6" /></svg>
            {u.role === "Admin" ? admin.makeXodim : admin.makeAdmin}
          </button>
          <div style={{ height: 1, background: "var(--adm-border-3)", margin: "6px 4px" }} />
          <button onClick={() => { onDelete(u.id); setMenu(false); }}
            style={{ display: "flex", width: "100%", alignItems: "center", gap: 9, padding: "9px 10px", border: "none", background: "transparent", color: "var(--adm-danger)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /></svg>
            {admin.delete}
          </button>
        </div>
      )}
    </div>
  );
}

export default function UsersTable({ users, search, onChangeRole, onDelete, onUpdate, t: admin, lang }: Props) {
  const [editing, setEditing] = useState<AdminUser | null>(null);
  return (
    <div className={styles.table}>
      <div className={styles.headRow}>
        <span>{admin.tableUser}</span><span>{admin.tableDept}</span><span>{admin.tableRole}</span><span>{admin.tableStatus}</span><span />
      </div>
      {users.map((u, i) => (
        <HoverRow key={u.id} user={u} last={i === users.length - 1} index={i} onChangeRole={onChangeRole} onDelete={onDelete} onEdit={setEditing} admin={admin} lang={lang} />
      ))}
      {users.length === 0 && <div className={styles.empty}>{admin.noUsersFound(search)}</div>}

      {editing && (
        <EditUserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSubmit={(input) => onUpdate(editing.id, input)}
          t={admin}
          lang={lang}
        />
      )}
    </div>
  );
}
