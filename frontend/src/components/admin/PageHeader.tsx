import { useNavigate } from "react-router-dom";
import { IoMdChatboxes } from "react-icons/io";
import HButton from "../common/HButton";
import ThemeToggle from "../chat/ThemeToggle";
import NotificationsBell from "../chat/NotificationsBell";
import { getThemeTokens } from "../chat/theme";
// Chatga o'tish tugmasi chat sahifasidagi "admin panel" tugmasining aynan
// o'zi bo'lishi uchun uslub ham o'sha yerdan olinadi.
import headerStyles from "../chat/ChatHeader.module.css";
import LangSwitcher from "../LangSwitcher";
import { chatStaticDict } from "../../locales";
import type { AdminView } from "../../types/admin";
import type { AdminStrings } from "../../types/i18n";
import type { Lang } from "../../types/lang";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  view: AdminView;
  search: string;
  setSearch: (v: string) => void;
  onAddUser: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
  lang: Lang;
  setLang: (l: Lang) => void;
  t: AdminStrings;
}

export default function PageHeader({ view, search, setSearch, onAddUser, isDark, onToggleTheme, lang, setLang, t: admin }: PageHeaderProps) {
  const navigate = useNavigate();
  // "Foydalanuvchi qo'shish" FAQAT "Foydalanuvchilar" sahifasida. Dashboard —
  // ko'rsatkichlar sahifasi, u yerda amal tugmasi turishi mantiqsiz edi
  // (ro'yxat ham yo'q, qo'shilgandan keyin natija ko'rinmasdi).
  const onUsers = view === "users";
  const titles: Record<AdminView, string> = {
    dashboard: admin.dashboardTitle,
    users: admin.usersTitle,
    reports: admin.reportsTitle,
    knowledgeList: admin.knowledgeTitle,
    pdfUpload: admin.pdfNav,
    apiDocs: "API hujjatlari",
  };
  return (
    <header className={styles.header}>
      <div>
        <div className={styles.title}>{titles[view]}</div>
      </div>
      <div className={styles.actions}>
        {/* Bildirishnomalar chatdagi bilan bir xil komponent — admin murojaat
            xabarini shu yerdan ham ko'ra oladi */}
        <NotificationsBell tk={getThemeTokens(isDark)} isDark={isDark} s={chatStaticDict[lang]} />
        {/* Chatga qaytish — chat sahifasidagi "admin panel" tugmasining
            ko'zgusi. Ilgari u yon panelda bo'lim sifatida turardi, lekin u
            BO'LIM emas, boshqa sahifaga o'tish — o'rni shu yerda. */}
        <HButton
          onClick={() => navigate("/")}
          data-tip={admin.chatNav}
          aria-label={admin.chatNav}
          className={`${headerStyles.adminBtn} tu-shiny tu-shiny-always`}
          baseStyle={{ border: "1px solid var(--tu-glass-border)", color: isDark ? "#E2E8F0" : "#193070", backdropFilter: "var(--tu-glass-blur)", WebkitBackdropFilter: "var(--tu-glass-blur)" }}
          hoverStyle={{ transform: "translateY(-1px)" }}
        >
          <IoMdChatboxes size={20} />
        </HButton>
        <LangSwitcher lang={lang} onChange={setLang} theme={isDark ? "dark" : "light"} align="right" tip={admin.selectLanguage} />
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} label={isDark ? admin.dayMode : admin.nightMode} />
        {onUsers && (
          <div className={styles.searchBox}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--adm-text-muted-2)" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            <input className={styles.searchInput} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={admin.searchUsersPh} />
          </div>
        )}
        {onUsers && (
          <HButton onClick={onAddUser} className={`${styles.addBtn} tu-shiny`} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)" }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            {admin.addUser}
          </HButton>
        )}
      </div>
    </header>
  );
}
