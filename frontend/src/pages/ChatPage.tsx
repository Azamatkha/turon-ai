import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLang } from "../hooks/useLang";
import { useChatHistory } from "../hooks/useChatHistory";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { useTheme } from "../contexts/ThemeContext";
import { chatDict, chatStaticDict } from "../locales";
import { fetchMe, logout, changePassword, updateProfile } from "../services/authService";
import { getThemeTokens, getSideTokens } from "../components/chat/theme";
import Sidebar, { SW, COLL } from "../components/chat/Sidebar";
import SidebarToggle from "../components/chat/SidebarToggle";
import ChatHeader from "../components/chat/ChatHeader";
import MessageArea from "../components/chat/MessageArea";
import Composer from "../components/chat/Composer";
import ProfileModal from "../components/chat/ProfileModal";
import Starfield from "../components/Starfield";
import GridPattern from "../components/GridPattern";
import OrbitRings from "../components/OrbitRings";
import Logo from "../components/common/Logo";
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

  // Tor ekranda sidebar kontent USTIGA suriladigan panel (drawer) bo'ladi va
  // sukut bo'yicha YOPIQ turadi — aks holda telefonda birinchi ko'rinadigan
  // narsa chat emas, suhbatlar ro'yxati bo'lardi.
  const isNarrow = useMediaQuery("(max-width: 900px)");
  const [sidebarOpen, setSidebarOpen] = useState(() => !window.matchMedia("(max-width: 900px)").matches);
  const [search, setSearch] = useState("");
  const { theme, toggleTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("user");
  const [pFullName, setPFullName] = useState("");
  const [pUsername, setPUsername] = useState("");
  const [pCurrentPassword, setPCurrentPassword] = useState("");
  const [pPassword, setPPassword] = useState("");
  const [pConfirmPassword, setPConfirmPassword] = useState("");
  const [pError, setPError] = useState("");
  const [pSaving, setPSaving] = useState(false);

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

  // Ekran torayganda drawer'ni yopamiz, kengayganda qaytaramiz — foydalanuvchi
  // oynani cho'zganda sidebar "osilib" qolmasligi uchun.
  useEffect(() => {
    setSidebarOpen(!isNarrow);
  }, [isNarrow]);

  // Drawer ochiq bo'lsa Esc uni yopadi (klaviatura bilan ishlaydiganlar uchun)
  useEffect(() => {
    if (!isNarrow || !sidebarOpen) return;
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [isNarrow, sidebarOpen]);

  // Xabarlar o'zgarganda pastga skroll.
  //
  // ILGARI: `chats` HAR QANDAY o'zgarishida shartsiz pastga sakrardi —
  // foydalanuvchi eski xabarni o'qiyotgan bo'lsa ham tortib tushirardi.
  // ENDI: faqat foydalanuvchi allaqachon pastga yaqin turgan bo'lsa
  // (yoki bot javob yozayotgan bo'lsa) skroll qilamiz.
  const scrollRef = useRef<HTMLDivElement>(null);
  const NEAR_BOTTOM_PX = 120;

  const isNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  }, []);

  // Foydalanuvchi o'zi yuqoriga surganini eslab qolamiz — yangi token kelganda
  // uni majburan pastga tortmaslik uchun.
  const stickToBottom = useRef(true);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      stickToBottom.current = isNearBottom();
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [isNearBottom]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [chats, thinking]);

  const openProfile = () => {
    setPFullName(fullName);
    setPUsername(username);
    setPCurrentPassword("");
    setPPassword("");
    setPConfirmPassword("");
    setPError("");
    setSaved(false);
    setProfileOpen(true);
  };

  // Profilni saqlash: ism/login (PATCH /v1/users/me) va parol
  // (PATCH /v1/users/me/password) — ikkitasi ALOHIDA endpoint.
  //
  // Tartib muhim: avval ism/login, keyin parol. Sababi parol o'zgarganda
  // backend BARCHA sessiyalarni bekor qiladi — undan keyingi har qanday
  // so'rov 401 bo'lardi. Ya'ni teskari tartibda ism saqlanmay qolardi.
  const saveProfile = async () => {
    setPError("");
    const nameChanged = pFullName.trim() !== fullName;
    const usernameChanged = pUsername.trim().toLowerCase() !== username;
    const wantsPasswordChange = !!pPassword;

    // Hech narsa o'zgarmagan bo'lsa — saqlaydigan narsa yo'q, oynani yopamiz
    if (!nameChanged && !usernameChanged && !wantsPasswordChange) {
      setProfileOpen(false);
      return;
    }

    if (wantsPasswordChange) {
      if (!pCurrentPassword) {
        setPError(S.currentPasswordRequired);
        return;
      }
      // O'zi to'g'ri terganini tekshirish uchun tasdiqlash bilan solishtiramiz
      if (pPassword !== pConfirmPassword) {
        setPError(S.passwordMismatch);
        return;
      }
    }

    setPSaving(true);
    try {
      if (nameChanged || usernameChanged) {
        const me = await updateProfile({
          ...(nameChanged ? { full_name: pFullName.trim() } : {}),
          ...(usernameChanged ? { username: pUsername.trim().toLowerCase() } : {}),
        });
        // Ekrandagi qiymatlarni backend QAYTARGANI bilan almashtiramiz —
        // u normalizatsiya qilingan bo'lishi mumkin (login kichik harfga
        // tushadi, ismdagi ortiqcha bo'shliqlar olib tashlanadi).
        setFullName(me.full_name);
        setUsername(me.username);
        setPFullName(me.full_name);
        setPUsername(me.username);
      }

      if (wantsPasswordChange) {
        await changePassword(pCurrentPassword, pPassword);
        // Parol o'zgardi -> backend hamma sessiyani o'chirdi -> hozirgi token
        // ham yaroqsiz. Foydalanuvchini yangi parol bilan qayta kirishga
        // yuboramiz, aks holda u har bir so'rovda 401 olib, sababini
        // tushunmasdi.
        await logout();
        navigate("/login");
        return;
      }
    } catch (e) {
      setPError(e instanceof Error ? e.message : "Saqlashda xatolik");
      return;
    } finally {
      setPSaving(false);
    }

    setPCurrentPassword("");
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

  // Login band-emasligi TEKSHIRUVI FAQAT BACKENDDA.
  //
  // Ilgari u `services/seedData` dagi TAKEN_USERNAMES — qo'lda yozilgan MOCK
  // ro'yxat bo'yicha ishlardi. Ya'ni haqiqiy bazada band bo'lgan login "bo'sh"
  // ko'rinishi, mock ro'yxatdagi bemalol login esa "band" ko'rinishi mumkin edi.
  //
  // Endi band login yuborilsa backend 409 + "Bu login allaqachon band" beradi
  // va u xato maydonida ko'rinadi. Har harf terilganda so'rov yuboradigan
  // jonli tekshiruv ataylab qo'shilmadi: u har bir foydalanuvchi uchun
  // o'nlab keraksiz so'rov degani, foydasi esa saqlashdagi bitta xabar.

  return (
    <div className={styles.page} style={{ background: tk.bg, color: tk.strong }}>
      {/* Klaviatura foydalanuvchisi uchun: Tab bosilganda birinchi bo'lib shu
          havola chiqadi va sidebar'dagi o'nlab suhbatni bosib o'tmasdan
          to'g'ridan-to'g'ri chatga o'tish imkonini beradi. */}
      <a href="#chat-main" className="skip-link">
        {S.skipToContent}
      </a>

      {/* Fon qatlami — statik CSS gradienti (ChatPage.module.css).
          Ilgari bu yerda to'liq ekranli WebGL raymarching shader
          (GradientWaves) va sichqonchaga javob beradigan canvas (DotField)
          ishlab turardi. Ikkalasi ham olib tashlandi: ofis kompyuterida ular
          doimiy GPU/CPU yuki edi, ko'rinadigan foydasi esa yo'q darajada. */}
      <div className={styles.bgLayer} aria-hidden="true" />

      {/* Tor ekranda drawer ortidagi qorayish — bosilganda panel yopiladi.
          <button>: klaviatura bilan ham yopish mumkin bo'lsin. */}
      {isNarrow && sidebarOpen && (
        <button
          type="button"
          className={styles.scrim}
          aria-label={S.closeSidebar}
          onClick={() => setSidebarOpen(false)}
        />
      )}

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

      <main className={styles.main} id="chat-main">
        {/* Fon: yoyilma -> to'r -> yulduzlar -> xira logotip. Hammasi
            mazmun maydoni ichida, shuning uchun yon panel ochilganda ham
            markaz joyida qoladi. */}
        <div className={styles.gradientBg} aria-hidden="true" />
        <GridPattern className={styles.gridBg} />
        <OrbitRings />
        <Starfield className={styles.spaceBg} isDark={isDark} />
        <div className={styles.bgLogo} aria-hidden="true"><Logo size={260} /></div>

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
            pCurrentPassword={pCurrentPassword}
            setPCurrentPassword={setPCurrentPassword}
            pPassword={pPassword}
            setPPassword={setPPassword}
            pConfirmPassword={pConfirmPassword}
            setPConfirmPassword={setPConfirmPassword}
            error={pError}
            saved={saved}
            saving={pSaving}
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
