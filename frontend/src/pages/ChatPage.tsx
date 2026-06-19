import { useState, useRef, useEffect, CSSProperties, KeyboardEvent, ButtonHTMLAttributes } from "react";
import { useNavigate } from "react-router-dom";

const ACCENT = "#3a7ca5";

// Turon AI logotipi
const Logo = ({ size = 26 }: { size?: number }) => (
  <svg viewBox="0 0 300 304" width={size} height={size} style={{ display: "block" }}>
    <path
      d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z"
      fill="currentColor"
    />
  </svg>
);

// Hover stilini qo'llab-quvvatlovchi tugma (inline-style uchun)
type HBProps = ButtonHTMLAttributes<HTMLButtonElement> & { baseStyle: CSSProperties; hoverStyle?: CSSProperties };
function HButton({ baseStyle, hoverStyle, ...props }: HBProps) {
  const [h, setH] = useState(false);
  return (
    <button
      {...props}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{ ...baseStyle, ...(h && hoverStyle ? hoverStyle : {}) }}
    />
  );
}

type Role = "user" | "assistant";
interface Msg { id: string; role: Role; text: string; }
interface Chat { id: string; group: string; title: string; messages: Msg[]; }

// Ikki tildagi matnlar
const STRINGS = {
  uz: {
    newChat: "Yangi suhbat",
    sub: "Istalgan narsani so‘rang, g‘oya o‘ylab toping yoki quyidan boshlang.",
    placeholder: "Turon AI’ga yozing…",
    disclaimer: "Turon AI xato qilishi mumkin. Muhim ma’lumotlarni tekshiring.",
    today: "Bugun",
    yest: "Kecha",
    prev: "Oxirgi 7 kun",
    sugg: ["Mijozga xat loyihasini tuz", "Bank mahsulotini tushuntir", "Hujjatni qisqacha bayon qil", "Operatsiya bo‘yicha yordam"],
    greeting: (n: string) => `Qanday yordam beraman, ${n}?`,
  },
  ru: {
    newChat: "Новый чат",
    sub: "Спросите что угодно, придумайте идеи или начните ниже.",
    placeholder: "Напишите Turon AI…",
    disclaimer: "Turon AI может ошибаться. Проверяйте важное.",
    today: "Сегодня",
    yest: "Вчера",
    prev: "Последние 7 дней",
    sugg: ["Составь письмо клиенту", "Объясни банковский продукт", "Кратко изложи документ", "Помощь по операции"],
    greeting: (n: string) => `Чем помочь, ${n}?`,
  },
} as const;
type Lang = keyof typeof STRINGS;

// Bot javobini (simulyatsiya) tanlash
function pickReply(t: string): string {
  const s = t.toLowerCase();
  if (/^(hi|hello|hey|salom|assalom)/.test(s))
    return "Salom! Men Turon AI — yordam berishdan xursandman. Biror narsani tushuntirish, matn yozish, reja tuzish yoki kod ustida ishlashni so‘rashingiz mumkin. Nima haqida gaplashamiz?";
  if (/\b(code|bug|python|javascript|error|function|kod|xato)\b/.test(s))
    return "Keling, birga ko‘rib chiqamiz. Kod parchasini va kutilgan natija bilan haqiqiy natijani yuboring — men muammoni bosqichма-bosqич topaman.";
  if (/\b(plan|strategy|marketing|roadmap|reja|strategiya)\b/.test(s))
    return "Mana toza tuzilma:\n\n1. Maqsad — choraklik bitta o‘lchanadigan maqsad.\n2. Auditoriya — kimga yetkazasiz va qaysi fikr ularni harakatga keltiradi.\n3. Kanallar — beshtani yarim qilgandan ko‘ra ikkitasini yaxshi qiling.\n4. Kalendar — muhim sanalar.\n5. Metrikalar — har hafta nimani tekshirasiz.\n\nBirortasini to‘liq yozib berayinmi?";
  if (/\b(explain|how|what|why|tushuntir|qanday|nima|nega)\b/.test(s))
    return "Yaxshi savol. Qisqasi: bu murakkab munosabatni bir nechta sodda, takrorlanadigan qoidaga aylantirishdir. Avval intuitsiyani, keyin aniq mexanikani beray — qay darajada chuqur tushuntirishni ayting.";
  return "Tushundim. Men bunday yondashardim: avval istagan natijani aniqlang, uni eng muhim ikki-uch qarorga bo‘ling, qolganini tafsilot sifatida hal qiling. Cheklovlaringizni ayting — aniqroq qilaman.";
}

export default function ChatPage() {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [lang, setLang] = useState<Lang>("uz");
  const [profileOpen, setProfileOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fullName, setFullName] = useState("Aziz Karimov");
  const [username, setUsername] = useState("a.karimov");
  const [pFullName, setPFullName] = useState("Aziz Karimov");
  const [pUsername, setPUsername] = useState("a.karimov");
  const [pPassword, setPPassword] = useState("");
  const [activeId, setActiveId] = useState("c1");
  const [chats, setChats] = useState<Chat[]>([
    { id: "c1", group: "Today", title: "", messages: [] },
    { id: "c2", group: "Today", title: "Mijozga kechikkan to‘lov xati", messages: [] },
    { id: "c3", group: "Yesterday", title: "Ipoteka refinansirovkasi shartlari", messages: [] },
    { id: "c4", group: "Yesterday", title: "KYC onboarding siyosati xulosasi", messages: [] },
    { id: "c5", group: "Previous 7 Days", title: "Karta nizosi javob shabloni", messages: [] },
    { id: "c6", group: "Previous 7 Days", title: "Korporativ depozit stavkalari", messages: [] },
    { id: "c7", group: "Previous 7 Days", title: "AML xavf belgilari ro‘yxati", messages: [] },
  ]);

  const TAKEN = ["admin", "root", "m.usmonov", "d.tashkentov", "s.rahimova"];
  const T = STRINGS[lang];
  const isDark = theme === "dark";
  const userName = fullName || "Aziz Karimov";
  const userHandle = "@" + (username || "user");
  const initial = userName.charAt(0).toUpperCase();
  const SW = 282;
  const COLL = 72;

  // Xabarlar o'zgarganда pastga skroll
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chats, thinking]);

  // Komponent yopilганда taymerni tozalash
  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const setActiveMsgs = (updater: (m: Msg[]) => Msg[]) =>
    setChats((cs) => cs.map((c) => (c.id === activeId ? { ...c, messages: updater(c.messages) } : c)));

  const openProfile = () => {
    setPFullName(fullName);
    setPUsername(username);
    setPPassword("");
    setSaved(false);
    setProfileOpen(true);
  };

  const saveProfile = () => {
    const u = pUsername.trim();
    if (!pFullName.trim() || !u || (TAKEN.includes(u) && u !== username)) return;
    setFullName(pFullName.trim());
    setUsername(u);
    setPPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const newChat = () => {
    const id = "c" + Date.now();
    setChats((cs) => [{ id, group: "Today", title: "", messages: [] }, ...cs]);
    setActiveId(id);
    setDraft("");
    setThinking(false);
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const onDraft = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDraft(e.target.value);
    const ta = taRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    }
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const respond = (userText: string) => {
    const full = pickReply(userText);
    const id = "a" + Date.now();
    setThinking(false);
    setActiveMsgs((m) => [...m, { id, role: "assistant", text: "" }]);
    const parts = full.split(/(\s+)/);
    let i = 0;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      i++;
      const partial = parts.slice(0, i).join("");
      setActiveMsgs((m) => m.map((x) => (x.id === id ? { ...x, text: partial } : x)));
      if (i >= parts.length && timerRef.current) clearInterval(timerRef.current);
    }, 26);
  };

  const send = (forced?: string) => {
    const text = (forced ?? draft).trim();
    if (!text || thinking) return;
    const um: Msg = { id: "u" + Date.now(), role: "user", text };
    setChats((cs) =>
      cs.map((c) => {
        if (c.id !== activeId) return c;
        const title = c.messages.length === 0 ? text.slice(0, 42) : c.title;
        return { ...c, title, messages: [...c.messages, um] };
      })
    );
    setDraft("");
    setThinking(true);
    const ta = taRef.current;
    if (ta) ta.style.height = "auto";
    setTimeout(() => respond(text), 750);
  };

  // ---- mavzu tokenlari ----
  const tk = isDark
    ? { bg: "#0e2735", headBg: "rgba(14,39,53,.82)", headBorder: "rgba(255,255,255,.08)", strong: "#e8eef2", muted: "#8aa1ae", card: "#16384a", cardBorder: "rgba(255,255,255,.08)", input: "#e8eef2", disc: "#6b8290", chipShadow: "none" }
    : { bg: "#f4f6f3", headBg: "rgba(244,246,243,.82)", headBorder: "#e7eae5", strong: "#16425b", muted: "#6b7d86", card: "#ffffff", cardBorder: "#e7e9e4", input: "#16425b", disc: "#9aa7a2", chipShadow: "0 1px 2px rgba(22,66,91,.04)" };
  const side = { bg: isDark ? "#102f41" : "#16425b", fg: "#eef2ef", sub: "rgba(217,220,214,.55)", active: "rgba(255,255,255,.13)", border: "rgba(255,255,255,.09)", logo: "#7fb3d2", btn: "rgba(255,255,255,.07)" };
  const sideHover: CSSProperties = { background: "rgba(255,255,255,.08)" };
  const btnHover: CSSProperties = { background: "rgba(255,255,255,.13)" };

  const railBtn: CSSProperties = { display: "flex", alignItems: "center", justifyContent: "center", width: "42px", height: "42px", borderRadius: "11px", border: "none", background: "transparent", color: side.fg, opacity: 0.82, cursor: "pointer", flex: "0 0 auto", transition: "background .15s ease" };
  const avatarSm: CSSProperties = { width: "32px", height: "32px", borderRadius: "9px", flex: "0 0 auto", background: `linear-gradient(140deg,${ACCENT},#3a7ca5)`, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "13.5px", fontWeight: 600 };
  const botAvatar: CSSProperties = { width: "30px", height: "30px", flex: "0 0 auto", borderRadius: "9px", background: `linear-gradient(140deg,#16425b,${ACCENT})`, display: "flex", alignItems: "center", justifyContent: "center", color: "#dbe7f0", boxShadow: "0 1px 3px rgba(22,66,91,.2)" };

  const order = ["Today", "Yesterday", "Previous 7 Days"];
  const labelMap: Record<string, string> = { Today: T.today, Yesterday: T.yest, "Previous 7 Days": T.prev };
  const groups = order
    .map((label) => ({
      label: labelMap[label],
      items: chats.filter((c) => c.group === label),
    }))
    .filter((g) => g.items.length);

  const active = chats.find((c) => c.id === activeId) || { messages: [], title: "" };
  const rawMsgs = active.messages || [];
  const isEmpty = rawMsgs.length === 0 && !thinking;
  const hasMessages = rawMsgs.length > 0 || thinking;
  const canSend = draft.trim().length > 0 && !thinking;

  const suggIcons = ["✦", "✎", "◷", "‹/›"];
  const usernameTaken = TAKEN.includes(pUsername.trim()) && pUsername.trim() !== username;
  const usernameOk = !!pUsername.trim() && pUsername.trim() !== username && !TAKEN.includes(pUsername.trim());

  return (
    <div style={{ height: "100vh", width: "100%", display: "flex", overflow: "hidden", background: tk.bg, color: tk.strong, transition: "background .35s ease, color .35s ease" }}>
      {/* ===== SIDEBAR ===== */}
      <aside
        style={{
          flex: `0 0 ${sidebarOpen ? SW : COLL}px`,
          width: (sidebarOpen ? SW : COLL) + "px",
          minWidth: 0,
          background: side.bg,
          color: side.fg,
          height: "100%",
          overflow: "hidden",
          borderRight: "1px solid " + side.border,
          transition: "flex-basis .38s cubic-bezier(.4,0,.2,1), width .38s cubic-bezier(.4,0,.2,1)",
        }}
      >
        {!sidebarOpen ? (
          // yig'ilgan (collapsed) rail
          <div style={{ width: COLL + "px", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: "7px", padding: "16px 0 14px" }}>
            <HButton onClick={() => setSidebarOpen(true)} title="Ochish" baseStyle={{ ...railBtn, opacity: 1, color: side.logo, animation: "floaty 5s ease-in-out infinite" }} hoverStyle={sideHover}>
              <Logo size={25} />
            </HButton>
            <div style={{ width: "26px", height: "1px", background: side.border, margin: "3px 0 5px" }} />
            <HButton onClick={newChat} title="Yangi suhbat" baseStyle={railBtn} hoverStyle={sideHover}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
            </HButton>
            <HButton onClick={() => setSidebarOpen(true)} title="Qidirish" baseStyle={railBtn} hoverStyle={sideHover}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            </HButton>
            <HButton onClick={() => setSidebarOpen(true)} title="Tarix" baseStyle={railBtn} hoverStyle={sideHover}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><line x1="8" y1="7" x2="20" y2="7" /><line x1="8" y1="12" x2="20" y2="12" /><line x1="8" y1="17" x2="20" y2="17" /><circle cx="4" cy="7" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="17" r="1" /></svg>
            </HButton>
            <div style={{ flex: 1 }} />
            <div style={avatarSm} title={userName}>{initial}</div>
          </div>
        ) : (
          // ochiq panel
          <div style={{ width: SW + "px", height: "100%", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 14px 16px 16px", borderBottom: "1px solid " + side.border, flex: "0 0 auto" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                <div style={{ width: "26px", height: "26px", flex: "0 0 auto", color: side.logo, animation: "floaty 5s ease-in-out infinite" }}><Logo size={26} /></div>
                <div style={{ fontSize: "17px", fontWeight: 700, letterSpacing: "-.3px", color: side.fg, whiteSpace: "nowrap" }}>
                  Turon<span style={{ fontWeight: 400, opacity: 0.7 }}> AI</span>
                </div>
              </div>
              <HButton onClick={() => setSidebarOpen(false)} title="Yig'ish" baseStyle={{ display: "flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", borderRadius: "8px", border: "none", background: "transparent", color: side.fg, opacity: 0.7, cursor: "pointer", flex: "0 0 auto", transition: "background .15s ease" }} hoverStyle={btnHover}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><rect x="3" y="4" width="18" height="16" rx="2.5" /><line x1="9.5" y1="4" x2="9.5" y2="20" /></svg>
              </HButton>
            </div>

            <div style={{ padding: "14px 14px 6px" }}>
              <HButton onClick={newChat} baseStyle={{ display: "flex", alignItems: "center", gap: "9px", width: "100%", padding: "11px 13px", borderRadius: "11px", border: "1px solid " + side.border, background: side.btn, color: side.fg, fontSize: "14px", fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap", transition: "all .18s ease" }} hoverStyle={{ ...btnHover, transform: "translateY(-2px)", boxShadow: "0 6px 16px rgba(0,0,0,.18)" }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                <span>{T.newChat}</span>
              </HButton>
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px 12px" }}>
              {groups.map((g) => (
                <div key={g.label}>
                  <div style={{ fontSize: "11px", fontWeight: 600, letterSpacing: ".6px", textTransform: "uppercase", color: side.sub, padding: "4px 11px 7px" }}>{g.label}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginBottom: "14px" }}>
                    {g.items.map((c) => {
                      const act = c.id === activeId;
                      return (
                        <HButton
                          key={c.id}
                          onClick={() => setActiveId(c.id)}
                          baseStyle={{ display: "flex", alignItems: "center", gap: "9px", width: "100%", padding: "9px 11px", borderRadius: "9px", border: "none", background: act ? side.active : "transparent", color: side.fg, fontSize: "13.5px", fontWeight: 500, cursor: "pointer", textAlign: "left", transition: "background .18s ease, transform .18s cubic-bezier(.2,.8,.3,1)" }}
                          hoverStyle={{ background: side.active, transform: "translateX(3px)" }}
                        >
                          <span style={{ width: "6px", height: "6px", borderRadius: "99px", flex: "0 0 auto", background: act ? side.logo : "transparent" }} />
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title || T.newChat}</span>
                        </HButton>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <HButton onClick={openProfile} baseStyle={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", padding: "11px 12px", border: "none", borderTop: "1px solid " + side.border, background: "transparent", color: side.fg, cursor: "pointer", flex: "0 0 auto", transition: "background .18s ease" }} hoverStyle={{ background: "rgba(255,255,255,.07)" }}>
              <div style={avatarSm}>{initial}</div>
              <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                <div style={{ fontSize: "13.5px", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{userName}</div>
                <div style={{ fontSize: "11.5px", color: side.sub, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{userHandle}</div>
              </div>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5, flex: "0 0 auto" }}><polyline points="9 18 15 12 9 6" /></svg>
            </HButton>
          </div>
        )}
      </aside>

      {/* ===== CHAT ===== */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, height: "100%", position: "relative" }}>
        {/* yuqori panel */}
        <header style={{ height: "60px", flex: "0 0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 18px", borderBottom: "1px solid " + tk.headBorder, background: tk.headBg, backdropFilter: "blur(8px)", position: "relative", zIndex: 3, transition: "background .35s ease, border-color .35s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
            {!sidebarOpen && (
              <HButton onClick={() => setSidebarOpen(true)} title="Ochish" baseStyle={{ display: "flex", alignItems: "center", justifyContent: "center", width: "34px", height: "34px", borderRadius: "9px", border: "none", background: "#fff", color: "#3a7ca5", cursor: "pointer", flex: "0 0 auto", boxShadow: "0 1px 3px rgba(22,66,91,.1)", transition: "all .18s ease" }} hoverStyle={{ background: "rgba(58,124,165,.1)" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><rect x="3" y="4" width="18" height="16" rx="2.5" /><line x1="9.5" y1="4" x2="9.5" y2="20" /></svg>
              </HButton>
            )}
            <div style={{ fontSize: "15px", fontWeight: 600, color: tk.strong, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "34vw" }}>{active.title || T.newChat}</div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {/* til almashtirgich */}
            <div style={{ display: "flex", alignItems: "center", gap: "2px", padding: "3px", borderRadius: "99px", background: isDark ? "rgba(255,255,255,.06)" : "rgba(22,66,91,.06)" }}>
              {(["uz", "ru"] as Lang[]).map((code) => {
                const on = lang === code;
                return (
                  <button key={code} onClick={() => setLang(code)} style={{ border: "none", cursor: "pointer", fontSize: "12px", fontWeight: 600, letterSpacing: ".3px", padding: "5px 11px", borderRadius: "99px", transition: "all .2s ease", background: on ? ACCENT : "transparent", color: on ? "#fff" : tk.muted, boxShadow: on ? "0 1px 3px rgba(22,66,91,.25)" : "none" }}>
                    {code === "uz" ? "UZB" : "RUS"}
                  </button>
                );
              })}
            </div>
            {/* mavzu tugmasi (light/dark) */}
            <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: isDark ? tk.muted : tk.strong, transition: "color .3s ease" }}>Light</span>
              <button onClick={() => setTheme(isDark ? "light" : "dark")} title="Mavzu" style={{ position: "relative", width: "60px", height: "30px", flex: "0 0 auto", borderRadius: "99px", border: "none", cursor: "pointer", padding: 0, background: isDark ? "#1b3340" : "linear-gradient(135deg,#7fb0e6,#a8c8f0)", boxShadow: isDark ? "inset 0 0 0 1px rgba(255,255,255,.08)" : "inset 0 1px 3px rgba(22,66,91,.2)", transition: "background .35s ease" }}>
                <span style={{ position: "absolute", top: "3px", left: "3px", width: "24px", height: "24px", borderRadius: "50%", background: isDark ? "#cdd7de" : "#fff", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 2px 5px rgba(0,0,0,.25)", transform: isDark ? "translateX(30px)" : "translateX(0)", transition: "transform .38s cubic-bezier(.5,1.6,.4,1), background .35s ease" }}>
                  {isDark && <svg width="14" height="14" viewBox="0 0 24 24" fill="#16425b"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" /></svg>}
                </span>
                <span style={{ position: "absolute", top: "8px", left: "14px", width: "3px", height: "3px", borderRadius: "50%", background: "#fff", opacity: isDark ? 0.9 : 0, transition: "opacity .35s ease" }} />
                <span style={{ position: "absolute", top: "17px", left: "20px", width: "2px", height: "2px", borderRadius: "50%", background: "#fff", opacity: isDark ? 0.7 : 0, transition: "opacity .35s ease" }} />
              </button>
              <span style={{ fontSize: "13px", fontWeight: 600, color: isDark ? tk.strong : tk.muted, transition: "color .3s ease" }}>Dark</span>
            </div>
          </div>
        </header>

        {/* xabarlar / bo'sh holat */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", position: "relative" }}>
          {isEmpty && (
            <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "32px 20px" }}>
              <div style={{ width: "64px", height: "64px", color: ACCENT, marginBottom: "22px", animation: "floaty 5s ease-in-out infinite" }}><Logo size={64} /></div>
              <div style={{ fontSize: "27px", fontWeight: 600, letterSpacing: "-.4px", color: tk.strong, marginBottom: "8px" }}>{T.greeting(userName)}</div>
              <div style={{ fontSize: "15px", color: tk.muted, maxWidth: "420px", marginBottom: "30px" }}>{T.sub}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", justifyContent: "center", maxWidth: "560px" }}>
                {T.sugg.map((label, idx) => (
                  <HButton key={label} onClick={() => send(label)} baseStyle={{ display: "flex", alignItems: "center", gap: "9px", padding: "11px 15px", background: tk.card, border: "1px solid " + tk.cardBorder, borderRadius: "13px", cursor: "pointer", fontSize: "13.5px", color: tk.strong, textAlign: "left", transition: "all .18s ease", boxShadow: tk.chipShadow }} hoverStyle={{ background: tk.card, borderColor: isDark ? "rgba(127,179,210,.5)" : "#bcd0e0", transform: "translateY(-2px)", boxShadow: isDark ? "0 6px 18px rgba(0,0,0,.3)" : "0 4px 14px rgba(22,66,91,.1)" }}>
                    <span style={{ fontSize: "15px" }}>{suggIcons[idx]}</span>
                    {label}
                  </HButton>
                ))}
              </div>
            </div>
          )}

          {hasMessages && (
            <div style={{ maxWidth: "760px", margin: "0 auto", padding: "28px 22px 16px", display: "flex", flexDirection: "column", gap: "20px" }}>
              {rawMsgs.map((m) => {
                const isUser = m.role === "user";
                return (
                  <div key={m.id} style={{ display: "flex", gap: "12px", justifyContent: isUser ? "flex-end" : "flex-start", alignItems: "flex-start", animation: "msgIn .35s cubic-bezier(.2,.7,.2,1) both" }}>
                    {!isUser && <div style={botAvatar}><Logo size={17} /></div>}
                    <div style={isUser
                      ? { maxWidth: "76%", background: ACCENT, color: "#fff", padding: "11px 16px", borderRadius: "18px 18px 5px 18px", fontSize: "14.5px", lineHeight: 1.55, whiteSpace: "pre-wrap", boxShadow: "0 1px 3px rgba(22,66,91,.18)" }
                      : { maxWidth: "80%", background: tk.card, color: tk.strong, padding: "13px 17px", borderRadius: "5px 18px 18px 18px", fontSize: "14.5px", lineHeight: 1.62, whiteSpace: "pre-wrap", border: "1px solid " + tk.cardBorder, boxShadow: isDark ? "none" : "0 1px 2px rgba(22,66,91,.04)" }}>
                      {m.text}
                    </div>
                  </div>
                );
              })}

              {thinking && (
                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start", animation: "msgIn .3s ease both" }}>
                  <div style={botAvatar}><Logo size={17} /></div>
                  <div style={{ display: "flex", gap: "5px", alignItems: "center", padding: "16px 18px", background: tk.card, border: "1px solid " + tk.cardBorder, borderRadius: "4px 18px 18px 18px" }}>
                    {[0, 0.18, 0.36].map((d) => (
                      <span key={d} style={{ width: "7px", height: "7px", borderRadius: "99px", background: "#3a7ca5", animation: "dot 1.3s infinite both", animationDelay: `${d}s` }} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* composer */}
        <div style={{ flex: "0 0 auto", padding: "10px 22px 16px", background: `linear-gradient(to top,${tk.bg} 60%,transparent)` }}>
          <div style={{ maxWidth: "760px", margin: "0 auto" }}>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", background: tk.card, border: "1px solid " + tk.cardBorder, borderRadius: "22px", padding: "8px 8px 8px 16px", boxShadow: isDark ? "0 4px 20px rgba(0,0,0,.3)" : "0 4px 20px rgba(22,66,91,.07)" }}>
              <textarea ref={taRef} value={draft} onChange={onDraft} onKeyDown={onKey} rows={1} placeholder={T.placeholder} style={{ flex: 1, border: "none", outline: "none", resize: "none", background: "transparent", fontSize: "15px", lineHeight: 1.5, color: tk.input, maxHeight: "160px", padding: "6px 4px" }} />
              <HButton onClick={() => send()} title="Yuborish" baseStyle={{ display: "flex", alignItems: "center", justifyContent: "center", width: "40px", height: "40px", flex: "0 0 auto", borderRadius: "50%", border: "none", background: canSend ? ACCENT : "#c4ccc9", cursor: canSend ? "pointer" : "default", transition: "background .2s ease, transform .15s ease" }} hoverStyle={canSend ? { transform: "scale(1.08)", background: "#16425b" } : {}}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="6" /><polyline points="6 12 12 6 18 12" /></svg>
              </HButton>
            </div>
            <div style={{ textAlign: "center", fontSize: "11.5px", color: tk.disc, marginTop: "9px" }}>{T.disclaimer}</div>
          </div>
        </div>

        {/* profil modal */}
        {profileOpen && (
          <div onClick={() => setProfileOpen(false)} style={{ position: "absolute", inset: 0, zIndex: 40, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px", background: "rgba(13,33,45,.42)", backdropFilter: "blur(3px)", animation: "fadeIn .2s ease both" }}>
            <div onClick={(e) => e.stopPropagation()} style={{ width: "100%", maxWidth: "420px", background: "#fff", borderRadius: "20px", padding: "26px", boxShadow: "0 24px 70px rgba(13,33,45,.4)", animation: "popIn .32s cubic-bezier(.2,.8,.3,1) both" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "13px", minWidth: 0 }}>
                  <div style={{ width: "52px", height: "52px", borderRadius: "15px", flex: "0 0 auto", background: `linear-gradient(140deg,${ACCENT},#3a7ca5)`, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "21px", fontWeight: 700 }}>{initial}</div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: "17px", fontWeight: 700, color: "#16425b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{pFullName}</div>
                    <div style={{ fontSize: "13px", color: "#7d909a" }}>{userHandle}</div>
                  </div>
                </div>
                <HButton onClick={() => setProfileOpen(false)} title="Yopish" baseStyle={{ display: "flex", alignItems: "center", justifyContent: "center", width: "34px", height: "34px", flex: "0 0 auto", borderRadius: "10px", border: "none", background: "#f1f4ef", color: "#5b6f78", cursor: "pointer", transition: "all .15s ease" }} hoverStyle={{ background: "#e6eae3", color: "#16425b" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
                </HButton>
              </div>

              <div style={{ height: "1px", background: "#e8ebe6", margin: "20px 0" }} />

              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px", letterSpacing: ".2px" }}>To‘liq ism</label>
                  <input value={pFullName} onChange={(e) => { setPFullName(e.target.value); setSaved(false); }} placeholder="Ismingiz" style={{ width: "100%", height: "46px", border: "1.6px solid #dde2dc", borderRadius: "11px", padding: "0 14px", fontSize: "14.5px", color: "#16425b", outline: "none", background: "#fbfcfa", transition: "border-color .18s ease" }} />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px", letterSpacing: ".2px" }}>Foydalanuvchi nomi</label>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", height: "46px", border: "1.6px solid #dde2dc", borderRadius: "11px", padding: "0 14px", background: "#fbfcfa" }}>
                    <span style={{ color: "#9aafb8", fontSize: "15px", flex: "0 0 auto" }}>@</span>
                    <input value={pUsername} onChange={(e) => { setPUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, "")); setSaved(false); }} placeholder="username" autoCapitalize="none" style={{ flex: 1, minWidth: 0, border: "none", outline: "none", background: "transparent", fontSize: "14.5px", color: "#16425b", height: "100%" }} />
                    {usernameTaken && <span style={{ color: "#c0392b", fontSize: "12px", fontWeight: 600, flex: "0 0 auto", whiteSpace: "nowrap" }}>Band</span>}
                    {usernameOk && <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#1f8a5b" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "0 0 auto" }}><polyline points="20 6 9 17 4 12" /></svg>}
                  </div>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px", letterSpacing: ".2px" }}>Yangi parol</label>
                  <input value={pPassword} onChange={(e) => { setPPassword(e.target.value); setSaved(false); }} type="password" placeholder="Bo‘sh qoldirsangiz — o‘zgarmaydi" autoComplete="new-password" style={{ width: "100%", height: "46px", border: "1.6px solid #dde2dc", borderRadius: "11px", padding: "0 14px", fontSize: "14.5px", color: "#16425b", outline: "none", background: "#fbfcfa", transition: "border-color .18s ease" }} />
                </div>
              </div>

              <HButton onClick={saveProfile} baseStyle={{ width: "100%", height: "48px", marginTop: "24px", display: "flex", alignItems: "center", justifyContent: "center", border: "none", borderRadius: "12px", cursor: "pointer", background: saved ? "#1f8a5b" : "linear-gradient(135deg,#2f6690,#16425b)", color: "#fff", fontSize: "15px", fontWeight: 600, boxShadow: "0 6px 18px rgba(22,66,91,.2)", transition: "all .2s ease" }} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(22,66,91,.28)" }}>
                {saved ? (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>Saqlandi
                  </span>
                ) : (
                  <span>O‘zgarishlarni saqlash</span>
                )}
              </HButton>

              <HButton onClick={() => navigate("/login")} baseStyle={{ width: "100%", height: "44px", marginTop: "10px", display: "flex", alignItems: "center", justifyContent: "center", gap: "9px", border: "1px solid #f0d5d2", borderRadius: "12px", cursor: "pointer", background: "#fff", color: "#c0392b", fontSize: "14px", fontWeight: 600, transition: "all .18s ease" }} hoverStyle={{ background: "#fdeceb", borderColor: "#ecc4c0" }}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                Chiqish
              </HButton>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
