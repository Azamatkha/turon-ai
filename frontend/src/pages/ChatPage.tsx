import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { useChatHistory } from "../hooks/useChatHistory";
import { useTheme } from "../contexts/ThemeContext";
import { chatDict, chatStaticDict } from "../locales";
import { TAKEN_USERNAMES } from "../services/seedData";
import { fetchMe, logout, changePassword } from "../services/authService";
import { getThemeTokens, getSideTokens } from "../components/chat/theme";
import GradientWaves from "../components/GradientWaves";
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
  const { sessionId } = useParams();
  const { lang, setLang, t: T } = useLang(chatDict);
  const S = chatStaticDict[lang]; // tanlangan tildagi statik matnlar
  const {
    chats, activeId, setActiveId, active, rawMsgs, isEmpty, hasMessages, canSend,
    draft, setDraft, thinking, generating, newChat, removeChat, togglePin, renameChat, send, stop, regenerate, editAndResend, voteMsg,
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
  const [pConfirmPassword, setPConfirmPassword] = useState("");
  const [pError, setPError] = useState("");

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

  // URL → holat: manzildagi sessionId (to'g'ridan-to'g'ri link yoki refresh) faol suhbatga aylanadi
  useEffect(() => {
    if (sessionId && sessionId !== activeId) setActiveId(sessionId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Holat → URL: faol suhbat o'zgarsa manzil ham mos bo'ladi (/c/<uuid>), yangi chatda "/"
  useEffect(() => {
    if (activeId && activeId !== sessionId) navigate(`/c/${activeId}`);
    else if (!activeId && sessionId) navigate("/");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

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
    setPConfirmPassword("");
    setPError("");
    setSaved(false);
    setProfileOpen(true);
  };

  const saveProfile = async () => {
    const u = pUsername.trim();
    if (!pFullName.trim() || !u) return;
    setPError("");
    // Parol kiritilgan bo'lsa — o'zi to'g'ri terganini tekshirish uchun tasdiqlash bilan solishtiramiz
    if (pPassword && pPassword !== pConfirmPassword) {
      setPError(S.passwordMismatch);
      return;
    }
    try {
      if (pPassword) await changePassword(pPassword);
    } catch (e) {
      setPError(e instanceof Error ? e.message : "Parolni o'zgartirishda xatolik");
      return;
    }
    // Ism/login hozircha faqat ekranda yangilanadi (backendda /me yangilash endpointi hali yo'q)
    setFullName(pFullName.trim());
    setUsername(u);
    setPPassword("");
    setPConfirmPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const tk = getThemeTokens(isDark);
  const side = getSideTokens(isDark);

  // Qidiruv matni bo'yicha suhbatlarni filtrlaymiz (sarlavha bo'yicha, registrga sezgir emas),
  // so'ng yagona (guruhlarsiz) ro'yxatda pin qilinganlar tepada, qolgani oxirgi xabar vaqti
  // bo'yicha (eng yangisi birinchi) chiqadi.
  const q = search.trim().toLowerCase();
  const visibleChats = q ? chats.filter((c) => (c.title || T.newChat).toLowerCase().includes(q)) : chats;
  // Vaqtni xavfsiz songa aylantiramiz — noto'g'ri/bo'sh sana NaN bermasin
  // (NaN saralashni beqaror qiladi: suhbat goh tepaga, goh o'rtaga tushardi).
  const ts = (v: string): number => {
    const t = new Date(v).getTime();
    return Number.isNaN(t) ? 0 : t;
  };
  const sortedChats = [...visibleChats].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    const byTime = ts(b.lastMessageAt) - ts(a.lastMessageAt);
    if (byTime !== 0) return byTime;
    // Vaqtlar teng (yoki noto'g'ri) bo'lsa — barqaror tartib, aks holda ro'yxat
    // tasodifiy joylashib qolardi
    return a.id < b.id ? 1 : -1;
  });

  const usernameTaken = TAKEN_USERNAMES.includes(pUsername.trim()) && pUsername.trim() !== username;
  const usernameOk = !!pUsername.trim() && pUsername.trim() !== username && !TAKEN_USERNAMES.includes(pUsername.trim());

  return (
    <div className={styles.page} style={{ background: tk.bg, color: tk.strong }}>
      {/* Fon qatlami — GradientWaves (raymarching to'lqinlar). Ranglar brend
          navydan olingan: light rejimda ochroq havorang, dark rejimda PRIMARY.
          Matn ostida turadi, shuning uchun opacity past ushlab turiladi. */}
      <div
        className={styles.bgLayer}
        aria-hidden="true"
        style={{ opacity: isDark ? 0.55 : 0.45 }}
      >
        <GradientWaves
          horizonColor={isDark ? "#0d1e33" : "#f3f5f8"}
          waveColor={isDark ? "#1B4B7A" : "#9dc0da"}
          crestColor={isDark ? "#7fb3d2" : "#ffffff"}
          speed={0.3}
          amplitude={2.5}
          waveScale={0.6}
          waveRatio={0.9}
          swell={35}
          turbulence={20}
          tilt={1.11}
          zoom={1}
          height={5.5}
          fogDepth={15}
          // "low" — 40 qadamli raymarch. Bu to'liq ekranli, har kadrda
          // hisoblanadigan shader; ofis kompyuterlarida "medium" og'irlik qiladi.
          detail="low"
          brightness={1}
          opacity={1}
          mouseInteraction
          parallaxStrength={0.4}
          grain
          grainIntensity={0.03}
        />
      </div>

      {/* Nuqta (DotField) qatlami — fon ustida, kursor bulge effekti bilan.
          Nuqtalar juda to'q bo'lib ketmasin: rang ham ochroq, qatlamning
          opacity'si ham past. */}
      <div
        className={styles.dotLayer}
        aria-hidden="true"
        style={{ opacity: isDark ? 0.3 : 0.4 }}
      >
        <DotField
          dotRadius={3.5}
          dotSpacing={26}
          bulgeOnly
          bulgeStrength={18}
          cursorRadius={220}
          glowRadius={160}
          gradientFrom={isDark ? "#2b4a6d" : "#b3c6d8"}
          gradientTo={isDark ? "#35597f" : "#a4bacf"}
          glowColor={isDark ? "rgba(127,179,210,0.10)" : "rgba(23,63,115,0.08)"}
        />
      </div>

      <Sidebar
        open={sidebarOpen}
        setOpen={setSidebarOpen}
        newChat={newChat}
        newChatLabel={T.newChat}
        chats={sortedChats}
        activeId={activeId}
        setActiveId={setActiveId}
        onRemoveChat={removeChat}
        onTogglePin={togglePin}
        removeChatLabel={S.removeChat}
        pinChatLabel={S.pinChat}
        unpinChatLabel={S.unpinChat}
        moreOptionsLabel={S.moreOptions}
        pinnedSectionLabel={S.pinnedSection}
        recentsSectionLabel={S.recentsSection}
        todayLabel={S.todayLabel}
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
          onEditResend={editAndResend}
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
            pConfirmPassword={pConfirmPassword}
            setPConfirmPassword={setPConfirmPassword}
            error={pError}
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
