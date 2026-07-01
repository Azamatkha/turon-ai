import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { useChatHistory } from "../hooks/useChatHistory";
import { useTheme } from "../contexts/ThemeContext";
import { chatDict, chatStaticDict } from "../locales";
import { TAKEN_USERNAMES } from "../services/seedData";
import { fetchMe, logout, changePassword } from "../services/authService";
import { getThemeTokens, getSideTokens } from "../components/chat/theme";
import DotField from "../components/DotField";
import Sidebar, { SW, COLL } from "../components/chat/Sidebar";
import SidebarToggle from "../components/chat/SidebarToggle";
import ChatHeader from "../components/chat/ChatHeader";
import MessageArea from "../components/chat/MessageArea";
import Composer from "../components/chat/Composer";
import ProfileModal from "../components/chat/ProfileModal";
import styles from "./ChatPage.module.css";

export default function ChatPage() {
  const navigate = useNavigate();
  const { lang, setLang, t: T } = useLang(chatDict);
  const S = chatStaticDict[lang]; // tanlangan tildagi statik matnlar
  const {
    chats, activeId, setActiveId, active, rawMsgs, isEmpty, hasMessages, canSend,
    draft, setDraft, thinking, generating, newChat, removeChat, renameChat, send, stop, regenerate, voteMsg,
  } = useChatHistory(T.newChat);

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [search, setSearch] = useState("");
  const { theme, toggleTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("user");
  const [pFullName, setPFullName] = useState("");
  const [pUsername, setPUsername] = useState("");
  const [pPassword, setPPassword] = useState("");

  // Haqiqiy foydalanuvchini backenddan olamiz (login token bilan)
  useEffect(() => {
    fetchMe()
      .then((me) => {
        setFullName(me.full_name);
        setUsername(me.username);
        setRole(me.role);
      })
      .catch(() => navigate("/login"));
  }, [navigate]);

  const isDark = theme === "dark";
  const userName = fullName || "Foydalanuvchi";
  const userHandle = "@" + (username || "user");
  const initial = userName.charAt(0).toUpperCase();

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  // Xabarlar o'zgarganda pastga skroll
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chats, thinking]);

  const openProfile = () => {
    setPFullName(fullName);
    setPUsername(username);
    setPPassword("");
    setSaved(false);
    setProfileOpen(true);
  };

  const saveProfile = async () => {
    const u = pUsername.trim();
    if (!pFullName.trim() || !u) return;
    try {
      // Parol kiritilgan bo'lsa — backendga yangi parolni yuboramiz
      if (pPassword) await changePassword(pPassword);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Parolni o'zgartirishda xatolik");
      return;
    }
    // Ism/login hozircha faqat ekranda yangilanadi (backendda /me yangilash endpointi hali yo'q)
    setFullName(pFullName.trim());
    setUsername(u);
    setPPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const tk = getThemeTokens(isDark);
  const side = getSideTokens(isDark);

  // Qidiruv matni bo'yicha suhbatlarni filtrlaymiz (sarlavha bo'yicha, registrga sezgir emas)
  const q = search.trim().toLowerCase();
  const visibleChats = q ? chats.filter((c) => (c.title || T.newChat).toLowerCase().includes(q)) : chats;

  const order = ["Today", "Yesterday", "Previous 7 Days"];
  const labelMap: Record<string, string> = { Today: T.today, Yesterday: T.yest, "Previous 7 Days": T.prev };
  const groups = order
    .map((label) => ({ label: labelMap[label], items: visibleChats.filter((c) => c.group === label) }))
    .filter((g) => g.items.length);

  const usernameTaken = TAKEN_USERNAMES.includes(pUsername.trim()) && pUsername.trim() !== username;
  const usernameOk = !!pUsername.trim() && pUsername.trim() !== username && !TAKEN_USERNAMES.includes(pUsername.trim());

  return (
    <div className={styles.page} style={{ background: tk.bg, color: tk.strong }}>
      {/* Juda mayin, brend rangidagi nuqta foni — matn o'qilishini buzmaslik uchun past shaffoflikda */}
      <div className={styles.bgLayer} aria-hidden="true">
        <DotField
          dotRadius={3.5}
          dotSpacing={26}
          bulgeOnly
          bulgeStrength={18}
          cursorRadius={220}
          glowRadius={160}
          gradientFrom={isDark ? "#22455c" : "#dbe3e8"}
          gradientTo={isDark ? "#2a5570" : "#cfdae0"}
          glowColor={isDark ? "rgba(127,179,210,0.10)" : "rgba(42,111,151,0.07)"}
        />
      </div>

      <Sidebar
        open={sidebarOpen}
        setOpen={setSidebarOpen}
        newChat={newChat}
        newChatLabel={T.newChat}
        groups={groups}
        activeId={activeId}
        setActiveId={setActiveId}
        onRemoveChat={removeChat}
        removeChatLabel={S.removeChat}
        search={search}
        setSearch={setSearch}
        searchPlaceholder={S.searchPlaceholder}
        noResultsLabel={S.noResults}
        side={side}
        userName={userName}
        userHandle={userHandle}
        initial={initial}
        openProfile={openProfile}
      />

      <SidebarToggle open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} left={sidebarOpen ? SW : COLL} openLabel={S.collapseSidebar} closedLabel={S.openSidebar} isDark={isDark} />

      <main className={styles.main}>
        <ChatHeader
          title={active.title || T.newChat}
          lang={lang}
          setLang={setLang}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          tk={tk}
          isAdmin={role === "admin"}
          onAdmin={() => navigate("/admin")}
          editableTitle={!!activeId && !!active.title}
          onRenameTitle={(next) => renameChat(activeId, next)}
          s={S}
        />

        <MessageArea
          scrollRef={scrollRef}
          isEmpty={isEmpty}
          hasMessages={hasMessages}
          greeting={T.greeting(userName)}
          sub={T.sub}
          suggestions={T.sugg}
          onSuggestionClick={(label) => send(label)}
          rawMsgs={rawMsgs}
          thinking={thinking}
          generating={generating}
          onRegenerate={regenerate}
          tk={tk}
          isDark={isDark}
          s={S}
          onVote={voteMsg}
        />

        <Composer
          draft={draft}
          setDraft={setDraft}
          canSend={canSend}
          onSend={() => send()}
          generating={generating}
          onStop={stop}
          placeholder={T.placeholder}
          disclaimer={T.disclaimer}
          tk={tk}
          isDark={isDark}
          s={S}
        />

        {profileOpen && (
          <ProfileModal
            initial={initial}
            userHandle={userHandle}
            pFullName={pFullName}
            setPFullName={setPFullName}
            pUsername={pUsername}
            setPUsername={setPUsername}
            usernameTaken={usernameTaken}
            usernameOk={usernameOk}
            pPassword={pPassword}
            setPPassword={setPPassword}
            saved={saved}
            onClose={() => setProfileOpen(false)}
            onSave={saveProfile}
            onLogout={doLogout}
            s={S}
            isDark={isDark}
          />
        )}
      </main>
    </div>
  );
}
