import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AdminRole, AdminUser, AdminView } from "../types/admin";
import {
  listUsers, createUser, changeRole, deleteUser, updateUser, type ApiUser, type BackendRole,
} from "../services/adminService";
import DotField from "../components/DotField";
import Sidebar from "../components/admin/Sidebar";
import PageHeader from "../components/admin/PageHeader";
import DashboardView from "../components/admin/DashboardView";
import UsersTable from "../components/admin/UsersTable";
import AddUserModal from "../components/admin/AddUserModal";
import styles from "./AdminPage.module.css";

// Faqat ikki rol: Admin va Xodim (oddiy foydalanuvchi).
const toAdminRole = (r: BackendRole): AdminRole => (r === "admin" ? "Admin" : "Xodim");
const toBackendRole = (r: AdminRole): BackendRole => (r === "Admin" ? "admin" : "user");

const mapUser = (u: ApiUser): AdminUser => ({
  id: u.id,
  name: u.full_name,
  handle: "@" + u.username,
  dept: u.department || "—",
  role: toAdminRole(u.role),
  status: u.is_active ? "Active" : "Suspended",
});

export default function AdminPage() {
  const navigate = useNavigate();
  const [view, setView] = useState<AdminView>("dashboard");
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);

  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [fName, setFName] = useState("");
  const [fUser, setFUser] = useState("");
  const [fDept, setFDept] = useState("");
  const [fPass, setFPass] = useState("");
  const [fRole, setFRole] = useState<AdminRole>("Xodim");

  // Foydalanuvchilarni serverdan yuklash (qidiruv/bo'lim o'zgarsa qayta)
  const load = async () => {
    try {
      const data = await listUsers(search, dept);
      setUsers(data.map(mapUser));
    } catch {
      setUsers([]);
    }
  };

  useEffect(() => {
    const id = setTimeout(load, 250); // debounce
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, dept]);

  useEffect(() => {
    setMounted(false);
    const r = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(r);
  }, [view]);

  const onDashboard = view === "dashboard";
  const onUsers = view === "users";

  const openAdd = () => {
    setFName(""); setFUser(""); setFDept(""); setFPass(""); setFRole("Xodim");
    setAdding(false); setAddOpen(true);
  };

  const submitAdd = async () => {
    if (!fName.trim() || !fUser.trim() || !fPass.trim()) return;
    setAdding(true);
    try {
      await createUser({
        username: fUser.trim(),
        full_name: fName.trim(),
        department: fDept.trim() || undefined,
        password: fPass,
        role: toBackendRole(fRole),
      });
      setAddOpen(false);
      await load();
    } catch {
      /* username band bo'lsa modal ochiq qoladi */
    } finally {
      setAdding(false);
    }
  };

  const onChangeRoleUser = async (id: string, role: AdminRole) => {
    await changeRole(id, toBackendRole(role));
    await load();
  };

  const onDeleteUser = async (id: string) => {
    await deleteUser(id);
    await load();
  };

  const onUpdateUser = async (
    id: string,
    input: { username?: string; full_name?: string; department?: string; password?: string }
  ) => {
    await updateUser(id, input);
    await load();
  };

  const handle = "@" + fUser.trim();
  const userTaken = !!fUser.trim() && users.some((u) => u.handle === handle);
  const departments = Array.from(new Set(users.map((u) => u.dept).filter((d) => d && d !== "—")));

  return (
    <div className={styles.page}>
      <div className={styles.bgLayer} aria-hidden="true">
        <DotField dotRadius={3.5} dotSpacing={26} bulgeOnly bulgeStrength={18} cursorRadius={220} glowRadius={160} gradientFrom="#dbe0e7" gradientTo="#cfd6df" glowColor="rgba(42,111,151,0.07)" />
      </div>

      <Sidebar view={view} setView={setView} usersCount={users.length} />

      <main className={styles.main}>
        <PageHeader onUsers={onUsers} search={search} setSearch={setSearch} onAddUser={openAdd} />

        <div className={styles.content}>
          {onDashboard && <DashboardView mounted={mounted} />}
          {onUsers && (
            <>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
                <button onClick={() => navigate("/")} style={{ padding: "8px 14px", borderRadius: 10, border: "1px solid #dde2dc", background: "#fff", color: "#173f73", cursor: "pointer", fontWeight: 600, fontSize: 13 }}>
                  ← Chat
                </button>
                <select value={dept} onChange={(e) => setDept(e.target.value)} style={{ padding: "8px 12px", borderRadius: 10, border: "1px solid #dde2dc", background: "#fff", color: "#173f73", fontSize: 13 }}>
                  <option value="">Barcha bo‘limlar</option>
                  {departments.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <UsersTable users={users} search={search} onChangeRole={onChangeRoleUser} onDelete={onDeleteUser} onUpdate={onUpdateUser} />
            </>
          )}
        </div>

        {addOpen && (
          <AddUserModal
            fName={fName} setFName={setFName}
            fUser={fUser} setFUser={setFUser}
            fDept={fDept} setFDept={setFDept}
            fPass={fPass} setFPass={setFPass}
            fRole={fRole} setFRole={setFRole}
            adding={adding} userTaken={userTaken}
            onClose={() => setAddOpen(false)} onSubmit={submitAdd}
          />
        )}
      </main>
    </div>
  );
}
