import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTheme } from "../contexts/ThemeContext";
import { useLang } from "../hooks/useLang";
import { adminDict } from "../locales";
import type { AdminRole, AdminUser, AdminView } from "../types/admin";
import {
  listUsers, createUser, changeRole, deleteUser, updateUser, getStats, type ApiUser, type BackendRole,
} from "../services/adminService";
import { scrapeUrl, uploadText } from "../services/knowledgeService";
import { listReports } from "../services/reportService";
import { DEFAULT_DEPARTMENT } from "../services/departments";
import DotField from "../components/DotField";
import Sidebar from "../components/admin/Sidebar";
import PageHeader from "../components/admin/PageHeader";
import DashboardView from "../components/admin/DashboardView";
import KnowledgeListView from "../components/admin/KnowledgeListView";
import PdfUploadView from "../components/admin/PdfUploadView";
import ApiDocsView from "../components/admin/ApiDocsView";
import ReportsView from "../components/admin/ReportsView";
import UsersTable from "../components/admin/UsersTable";
import AddUserModal from "../components/admin/AddUserModal";
import ScrapeModal, { type ScrapeProgress } from "../components/admin/ScrapeModal";
import FilterSelect from "../components/admin/FilterSelect";
import SidebarToggle from "../components/chat/SidebarToggle";
import styles from "./AdminPage.module.css";

// Faqat ikki rol: Admin va Xodim (oddiy foydalanuvchi).
const toAdminRole = (r: BackendRole): AdminRole => (r === "admin" ? "Admin" : "Xodim");
const toBackendRole = (r: AdminRole): BackendRole => (r === "Admin" ? "admin" : "user");

// Ochiq sahifa <-> manzildagi bo'lak (/admin/users, /admin/knowledge ...)
const VIEW_TO_PATH: Record<AdminView, string> = {
  dashboard: "dashboard",
  users: "users",
  reports: "reports",
  knowledgeList: "knowledge",
  pdfUpload: "documents",
  apiDocs: "api-docs",
};
const PATH_TO_VIEW: Record<string, AdminView> = {
  dashboard: "dashboard",
  users: "users",
  reports: "reports",
  knowledge: "knowledgeList",
  documents: "pdfUpload",
  "api-docs": "apiDocs",
};

const mapUser = (u: ApiUser): AdminUser => ({
  id: u.id,
  name: u.full_name,
  handle: "@" + u.username,
  dept: u.department || "—",
  role: toAdminRole(u.role),
  status: u.is_online ? "Online" : "Offline",
});

export default function AdminPage() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const { lang, setLang, t } = useLang(adminDict);
  // Manzildagi bo'lak <-> ochiq sahifa. Shu tufayli refresh qilinganda yoki
  // to'g'ridan-to'g'ri link ochilganda o'sha sahifa qoladi (dashboardga qaytmaydi).
  const { view: viewParam } = useParams();
  const navigate = useNavigate();
  const [view, setView] = useState<AdminView>(
    () => PATH_TO_VIEW[viewParam ?? ""] ?? "dashboard"
  );

  // URL -> holat (orqaga/oldinga tugmalari, to'g'ridan-to'g'ri link)
  useEffect(() => {
    const v = PATH_TO_VIEW[viewParam ?? ""];
    if (v && v !== view) setView(v);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewParam]);

  // Holat -> URL (sahifa almashsa manzil ham mos bo'ladi)
  useEffect(() => {
    const path = VIEW_TO_PATH[view];
    if (viewParam !== path) navigate(`/admin/${path}`, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [allDepts, setAllDepts] = useState<string[]>([]); // filter uchun barqaror ro'yxat
  const [navCollapsed, setNavCollapsed] = useState(false);
  // Sidebar'dagi "yangi murojaatlar" belgisi
  const [newReportsCount, setNewReportsCount] = useState(0);
  // Ro'yxat yuklash/rol o'zgartirish/o'chirish kabi amallar uchun umumiy xato banneri
  const [pageError, setPageError] = useState("");

  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addErr, setAddErr] = useState("");
  const [fName, setFName] = useState("");
  const [fUser, setFUser] = useState("");
  const [fDept, setFDept] = useState("");
  const [fPass, setFPass] = useState("");
  const [fRole, setFRole] = useState<AdminRole>("Xodim");

  const [scrapeOpen, setScrapeOpen] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [scrapeUrlValue, setScrapeUrlValue] = useState("");
  const [scrapeErr, setScrapeErr] = useState<string | null>(null);
  const [scrapeProgress, setScrapeProgress] = useState<ScrapeProgress | null>(null);
  // Qo'lda matn qo'shish rejimi maydonlari (havola modalining ikkinchi tabi)
  const [manTitle, setManTitle] = useState("");
  const [manText, setManText] = useState("");
  const [knowledgeReloadKey, setKnowledgeReloadKey] = useState(0);

  // Foydalanuvchilarni serverdan yuklash (qidiruv/bo'lim o'zgarsa qayta)
  const load = async () => {
    try {
      const data = await listUsers(search, dept);
      setUsers(data.map(mapUser));
      setPageError("");
    } catch (e) {
      setUsers([]);
      setPageError(e instanceof Error ? e.message : t.usersLoadError);
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
      // Filtr — BARCHA foydalanuvchi bo'limlari (chatdan foydalanmaganlar ham)
      setAllDepts(s.all_departments ?? []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refreshDepts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Yangi murojaatlar soni — sahifa ochilishida bir marta (belgini ko'rsatish uchun)
  useEffect(() => {
    listReports({ size: 1 })
      .then((d) => setNewReportsCount(d.new_count))
      .catch(() => {
        /* huquqi yo'q yoki tarmoq xatosi — belgi ko'rinmaydi */
      });
  }, []);

  useEffect(() => {
    setMounted(false);
    const r = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(r);
  }, [view]);

  const onDashboard = view === "dashboard";
  const onUsers = view === "users";
  const onReports = view === "reports";
  const onKnowledgeList = view === "knowledgeList";
  const onPdfUpload = view === "pdfUpload";
  const onApiDocs = view === "apiDocs";

  const openAdd = () => {
    // Bo'lim MAJBURIY — bo'sh qoldirib bo'lmaydi. Modal ochilishida darrov
    // "Boshqa" tanlangan bo'ladi, admin uni almashtiradi. Aks holda bo'limsiz
    // xodimlar qo'shilib, statistika va bo'lim bo'yicha qidiruv buzilardi.
    setFName(""); setFUser(""); setFDept(DEFAULT_DEPARTMENT); setFPass(""); setFRole("Xodim");
    setAdding(false); setAddErr(""); setAddOpen(true);
  };

  const submitAdd = async () => {
    if (!fName.trim() || !fUser.trim() || !fPass.trim()) return;
    setAdding(true);
    setAddErr("");
    try {
      await createUser({
        username: fUser.trim(),
        full_name: fName.trim(),
        // Kafolat: qandaydir yo'l bilan bo'sh qolsa ham "Boshqa" yuboriladi.
        department: fDept.trim() || DEFAULT_DEPARTMENT,
        password: fPass,
        role: toBackendRole(fRole),
      });
      setAddOpen(false);
      await load();
      await refreshDepts(); // yangi bo'lim qo'shilgan bo'lishi mumkin
    } catch (e) {
      // masalan username band bo'lsa — modal ochiq qoladi va xato ko'rsatiladi
      setAddErr(e instanceof Error ? e.message : t.saveFailed);
    } finally {
      setAdding(false);
    }
  };

  const onChangeRoleUser = async (id: string, role: AdminRole) => {
    try {
      await changeRole(id, toBackendRole(role));
      await load();
    } catch (e) {
      setPageError(e instanceof Error ? e.message : t.saveFailed);
    }
  };

  const onDeleteUser = async (id: string) => {
    try {
      await deleteUser(id);
      await load();
    } catch (e) {
      setPageError(e instanceof Error ? e.message : t.saveFailed);
    }
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
    setScrapeUrlValue(""); setManTitle(""); setManText("");
    setScrapeErr(null); setScraping(false); setScrapeProgress(null); setScrapeOpen(true);
  };

  // Qo'lda kiritilgan sarlavha+matnni to'g'ridan-to'g'ri bazaga yozadi
  const submitManualText = async () => {
    const title = manTitle.trim();
    const text = manText.trim();
    if (!title || !text) {
      setScrapeErr(t.knowledgeTextRequired);
      return;
    }
    setScraping(true);
    setScrapeErr(null);
    try {
      await uploadText(title, text);
      setScrapeOpen(false);
      setKnowledgeReloadKey((k) => k + 1);
    } catch (e) {
      setScrapeErr(e instanceof Error ? e.message : t.knowledgeScrapeError);
    } finally {
      setScraping(false);
    }
  };

  const submitScrape = async () => {
    // Har qatorda bitta havola — bo'sh qatorlar va dublikatlar tashlab yuboriladi
    const urls = Array.from(
      new Set(scrapeUrlValue.split("\n").map((u) => u.trim()).filter(Boolean))
    );
    if (urls.length === 0) {
      setScrapeErr(t.knowledgeUrlRequired);
      return;
    }
    setScraping(true);
    setScrapeErr(null);

    if (urls.length === 1) {
      // Bitta havola — oddiy oqim, alohida bulk API shart emas
      try {
        await scrapeUrl(urls[0]);
        setScrapeOpen(false);
        setKnowledgeReloadKey((k) => k + 1);
      } catch (e) {
        setScrapeErr(e instanceof Error ? e.message : t.knowledgeScrapeError);
      } finally {
        setScraping(false);
      }
      return;
    }

    // Ko'p havola — ketma-ket (for loop), har birida progress yangilanadi.
    // Jarayon davomida oyna yopilmaydi (ScrapeModal buni o'zi bloklaydi).
    let ok = 0;
    let fail = 0;
    setScrapeProgress({ done: 0, total: urls.length });
    for (const u of urls) {
      try {
        await scrapeUrl(u);
        ok += 1;
      } catch {
        fail += 1;
      }
      setScrapeProgress({ done: ok + fail, total: urls.length });
    }
    setScraping(false);
    setScrapeProgress(null);
    setKnowledgeReloadKey((k) => k + 1);
    if (fail > 0) {
      setScrapeErr(t.knowledgeBulkSummary(ok, fail)); // xato bo'lsa oyna ochiq qoladi, natija ko'rinadi
    } else {
      setScrapeOpen(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.bgLayer} aria-hidden="true">
        <DotField dotRadius={3.5} dotSpacing={26} bulgeOnly bulgeStrength={18} cursorRadius={220} glowRadius={160} gradientFrom={isDark ? "#22455c" : "#dbe0e7"} gradientTo={isDark ? "#2a5570" : "#cfd6df"} glowColor={isDark ? "rgba(96,165,250,0.10)" : "rgba(37,99,235,0.07)"} />
      </div>

      <Sidebar
        view={view}
        setView={setView}
        usersCount={users.length}
        newReportsCount={newReportsCount}
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
          {onUsers && pageError && (
            <div style={{ marginBottom: 14, padding: "10px 13px", borderRadius: 10, background: "var(--adm-danger-bg)", border: "1px solid var(--adm-danger-border)", color: "var(--adm-danger)", fontSize: 13, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
              <span>{pageError}</span>
              <button onClick={() => setPageError("")} aria-label={t.knowledgeCancel} style={{ border: "none", background: "transparent", color: "inherit", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
            </div>
          )}
          {onDashboard && <DashboardView mounted={mounted} t={t} />}
          {onKnowledgeList && <KnowledgeListView key={knowledgeReloadKey} mounted={mounted} t={t} onAddClick={openScrape} />}
          {onPdfUpload && (
            <PdfUploadView mounted={mounted} t={t} onUploaded={() => setKnowledgeReloadKey((k) => k + 1)} />
          )}
          {onReports && (
            <ReportsView mounted={mounted} t={t} onCountsChange={setNewReportsCount} />
          )}
          {onApiDocs && <ApiDocsView />}
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
              <UsersTable users={users} search={search} onChangeRole={onChangeRoleUser} onDelete={onDeleteUser} onUpdate={onUpdateUser} t={t} lang={lang} />
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
            adding={adding} userTaken={userTaken} error={addErr}
            onClose={() => setAddOpen(false)} onSubmit={submitAdd}
            t={t}
            lang={lang}
          />
        )}

        {scrapeOpen && (
          <ScrapeModal
            url={scrapeUrlValue} setUrl={setScrapeUrlValue}
            manTitle={manTitle} setManTitle={setManTitle}
            manText={manText} setManText={setManText}
            loading={scraping} error={scrapeErr} progress={scrapeProgress}
            onClose={() => setScrapeOpen(false)}
            onSubmitUrl={submitScrape} onSubmitText={submitManualText}
            t={t}
          />
        )}
      </main>
    </div>
  );
}
