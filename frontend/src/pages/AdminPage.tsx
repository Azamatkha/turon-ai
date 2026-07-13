import { useEffect, useState } from "react";
import { useTheme } from "../contexts/ThemeContext";
import { useLang } from "../hooks/useLang";
import { adminDict } from "../locales";
import type { AdminRole, AdminUser, AdminView } from "../types/admin";
import {
  listUsers, createUser, changeRole, deleteUser, updateUser, getStats, type ApiUser, type BackendRole,
} from "../services/adminService";
import { scrapeUrl } from "../services/knowledgeService";
import DotField from "../components/DotField";
import Sidebar from "../components/admin/Sidebar";
import PageHeader from "../components/admin/PageHeader";
import DashboardView from "../components/admin/DashboardView";
import KnowledgeListView from "../components/admin/KnowledgeListView";
import UsersTable from "../components/admin/UsersTable";
import AddUserModal from "../components/admin/AddUserModal";
import ScrapeModal from "../components/admin/ScrapeModal";
import FilterSelect from "../components/admin/FilterSelect";
import SidebarToggle from "../components/chat/SidebarToggle";
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
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const { lang, setLang, t } = useLang(adminDict);
  const [view, setView] = useState<AdminView>("dashboard");
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [allDepts, setAllDepts] = useState<string[]>([]); // filter uchun barqaror ro'yxat
  const [navCollapsed, setNavCollapsed] = useState(false);

  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [fName, setFName] = useState("");
  const [fUser, setFUser] = useState("");
  const [fDept, setFDept] = useState("");
  const [fPass, setFPass] = useState("");
  const [fRole, setFRole] = useState<AdminRole>("Xodim");

  const [scrapeOpen, setScrapeOpen] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [scrapeUrlValue, setScrapeUrlValue] = useState("");
  const [scrapeErr, setScrapeErr] = useState<string | null>(null);
  const [knowledgeReloadKey, setKnowledgeReloadKey] = useState(0);

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

  // Filter uchun barcha bo'limlar (filtrlangan userlardan emas — barqaror manba)
  const refreshDepts = async () => {
    try {
      const s = await getStats();
      setAllDepts(s.departments.map((d) => d.name).filter((n) => n !== "Boshqa"));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refreshDepts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setMounted(false);
    const r = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(r);
  }, [view]);

  const onDashboard = view === "dashboard";
  const onUsers = view === "users";
  const onKnowledgeList = view === "knowledgeList";

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
      await refreshDepts(); // yangi bo'lim qo'shilgan bo'lishi mumkin
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

  const openScrape = () => {
    setScrapeUrlValue(""); setScrapeErr(null); setScraping(false); setScrapeOpen(true);
  };

  const submitScrape = async () => {
    if (!scrapeUrlValue.trim()) {
      setScrapeErr(t.knowledgeUrlRequired);
      return;
    }
    setScraping(true);
    setScrapeErr(null);
    try {
      await scrapeUrl(scrapeUrlValue);
      setScrapeOpen(false);
      setKnowledgeReloadKey((k) => k + 1); // ro'yxatni qayta yuklash uchun KnowledgeListView'ni remount qilamiz
    } catch (e) {
      setScrapeErr(e instanceof Error ? e.message : t.knowledgeScrapeError);
    } finally {
      setScraping(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.bgLayer} aria-hidden="true">
        <DotField dotRadius={3.5} dotSpacing={26} bulgeOnly bulgeStrength={18} cursorRadius={220} glowRadius={160} gradientFrom={isDark ? "#22455c" : "#dbe0e7"} gradientTo={isDark ? "#2a5570" : "#cfd6df"} glowColor={isDark ? "rgba(127,179,210,0.10)" : "rgba(42,111,151,0.07)"} />
      </div>

      <Sidebar
        view={view}
        setView={setView}
        usersCount={users.length}
        collapsed={navCollapsed}
        t={t}
      />

      <SidebarToggle
        open={!navCollapsed}
        onToggle={() => setNavCollapsed((v) => !v)}
        left={navCollapsed ? 76 : 248}
      />

      <main className={styles.main}>
        <PageHeader
          view={view} search={search} setSearch={setSearch} onAddUser={openAdd}
          isDark={isDark} onToggleTheme={toggleTheme}
          lang={lang} setLang={setLang} t={t}
        />

        <div className={styles.content}>
          {onDashboard && <DashboardView mounted={mounted} t={t} />}
          {onKnowledgeList && <KnowledgeListView key={knowledgeReloadKey} mounted={mounted} t={t} onAddClick={openScrape} />}
          {onUsers && (
            <>
              <div style={{ marginBottom: 14 }}>
                <FilterSelect
                  value={dept}
                  onChange={setDept}
                  options={[
                    { value: "", label: t.allDepts },
                    ...allDepts.map((d) => ({ value: d, label: d })),
                  ]}
                />
              </div>
              <UsersTable users={users} search={search} onChangeRole={onChangeRoleUser} onDelete={onDeleteUser} onUpdate={onUpdateUser} t={t} />
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
            t={t}
          />
        )}

        {scrapeOpen && (
          <ScrapeModal
            url={scrapeUrlValue} setUrl={setScrapeUrlValue}
            loading={scraping} error={scrapeErr}
            onClose={() => setScrapeOpen(false)} onSubmit={submitScrape}
            t={t}
          />
        )}
      </main>
    </div>
  );
}
