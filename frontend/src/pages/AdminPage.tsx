import { useEffect, useState } from "react";
import type { AdminRole, AdminUser, AdminView } from "../types/admin";
import { seedAdminUsers } from "../services/seedData";
import DotField from "../components/DotField";
import Sidebar from "../components/admin/Sidebar";
import PageHeader from "../components/admin/PageHeader";
import DashboardView from "../components/admin/DashboardView";
import UsersTable from "../components/admin/UsersTable";
import AddUserModal from "../components/admin/AddUserModal";
import styles from "./AdminPage.module.css";

export default function AdminPage() {
  const [view, setView] = useState<AdminView>("dashboard");
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [fName, setFName] = useState("");
  const [fUser, setFUser] = useState("");
  const [fDept, setFDept] = useState("");
  const [fRole, setFRole] = useState<AdminRole>("Agent");
  const [users, setUsers] = useState<AdminUser[]>(seedAdminUsers);

  // View almashganda grafik animatsiyasini qayta ishga tushirish
  useEffect(() => {
    setMounted(false);
    const r = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(r);
  }, [view]);

  const onDashboard = view === "dashboard";
  const onUsers = view === "users";

  const openAdd = () => {
    setFName("");
    setFUser("");
    setFDept("");
    setFRole("Agent");
    setAdding(false);
    setAddOpen(true);
  };

  const submitAdd = () => {
    const handle = "@" + fUser.trim();
    if (!fName.trim() || !fUser.trim() || users.some((u) => u.handle === handle)) return;
    setAdding(true);
    setTimeout(() => {
      setUsers((us) => [{ id: Date.now(), name: fName.trim(), handle, dept: fDept.trim() || "—", role: fRole, status: "Invited" }, ...us]);
      setAdding(false);
      setAddOpen(false);
    }, 850);
  };

  const q = search.trim().toLowerCase();
  const filtered = users.filter((u) => !q || u.name.toLowerCase().includes(q) || u.handle.toLowerCase().includes(q) || u.dept.toLowerCase().includes(q));
  const handle = "@" + fUser.trim();
  const userTaken = !!fUser.trim() && users.some((u) => u.handle === handle);

  return (
    <div className={styles.page}>
      {/* Juda mayin, brend rangidagi nuqta foni (chat sahifasi bilan bir xil uslub) */}
      <div className={styles.bgLayer} aria-hidden="true">
        <DotField
          dotRadius={3.5}
          dotSpacing={26}
          bulgeOnly
          bulgeStrength={18}
          cursorRadius={220}
          glowRadius={160}
          gradientFrom="#dbe0e7"
          gradientTo="#cfd6df"
          glowColor="rgba(42,111,151,0.07)"
        />
      </div>

      <Sidebar view={view} setView={setView} usersCount={users.length} />

      <main className={styles.main}>
        <PageHeader onUsers={onUsers} search={search} setSearch={setSearch} onAddUser={openAdd} />

        <div className={styles.content}>
          {onDashboard && <DashboardView mounted={mounted} />}
          {onUsers && <UsersTable users={filtered} search={search} />}
        </div>

        {addOpen && (
          <AddUserModal
            fName={fName}
            setFName={setFName}
            fUser={fUser}
            setFUser={setFUser}
            fDept={fDept}
            setFDept={setFDept}
            fRole={fRole}
            setFRole={setFRole}
            adding={adding}
            userTaken={userTaken}
            onClose={() => setAddOpen(false)}
            onSubmit={submitAdd}
          />
        )}
      </main>
    </div>
  );
}
