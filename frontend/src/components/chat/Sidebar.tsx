import { CSSProperties, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { RiDeleteBin5Fill, RiMore2Fill, RiPushpin2Fill, RiPushpin2Line } from "react-icons/ri";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import { PRIMARY } from "./theme";
import type { Chat, SideTokens } from "../../types/chat";
import styles from "./Sidebar.module.css";

const SW = 282;
const COLL = 72;

interface SidebarProps {
  open: boolean;
  setOpen: (v: boolean) => void;
  newChat: () => void;
  newChatLabel: string;
  chats: Chat[];
  activeId: string;
  setActiveId: (id: string) => void;
  onRemoveChat: (id: string) => void;
  onTogglePin: (id: string) => void;
  removeChatLabel: string;
  pinChatLabel: string;
  unpinChatLabel: string;
  moreOptionsLabel: string;
  pinnedSectionLabel: string;
  recentsSectionLabel: string;
  todayLabel: string;
  search: string;
  setSearch: (v: string) => void;
  searchPlaceholder: string;
  noResultsLabel: string;
  side: SideTokens;
  userName: string;
  userHandle: string;
  initial: string;
  openProfile: () => void;
}

// Oxirgi xabar vaqtini menyu uchun formatlaydi: bugun bo'lsa "Bugun · soat:daqiqa",
// aks holda sana + vaqt (raqamli format — barcha tillarda bir xil ishlaydi)
function formatLastMessageTime(iso: string, todayLabel: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  if (d.toDateString() === now.toDateString()) return `${todayLabel} · ${time}`;
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${time}`;
}

export default function Sidebar({
  open, setOpen, newChat, newChatLabel, chats, activeId, setActiveId, onRemoveChat, onTogglePin,
  removeChatLabel, pinChatLabel, unpinChatLabel, moreOptionsLabel, pinnedSectionLabel, recentsSectionLabel, todayLabel,
  search, setSearch, searchPlaceholder, noResultsLabel,
  side, userName, userHandle, initial, openProfile,
}: SidebarProps) {
  const sideHover: CSSProperties = { background: "rgba(255,255,255,.08)" };
  const btnHover: CSSProperties = { background: "rgba(255,255,255,.13)" };
  const searchRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  // Qaysi qatorning "..." menyusi ochiq (id + ekrandagi joylashuvi) — bir vaqtda faqat bittasi.
  // Menyu <body>ga portal qilib chiqariladi — shunda sidebar ro'yxatining overflow/rang
  // qatlamlariga qo'shilib ketmaydi va har doim yaxshi ko'rinadi.
  const MENU_W = 180;
  const [menu, setMenu] = useState<{ id: string; top: number; left: number } | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const anchorElRef = useRef<HTMLElement | null>(null);

  const openMenu = (e: React.MouseEvent<HTMLButtonElement>, id: string) => {
    e.stopPropagation();
    if (menu?.id === id) { setMenu(null); return; }
    const rect = e.currentTarget.getBoundingClientRect();
    anchorElRef.current = e.currentTarget;
    setMenu({
      id,
      top: rect.bottom + 6,
      left: Math.min(Math.max(rect.right - MENU_W, 8), window.innerWidth - MENU_W - 8),
    });
  };

  // Menyu ochiq bo'lsa: tashqariga bosilganda yoki ro'yxat scroll qilinganda yopamiz
  // (scroll'da yopamiz, chunki joylashuv fixed va qayta hisoblanmaydi)
  useEffect(() => {
    if (!menu) return;
    const onDocMouseDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (menuRef.current?.contains(t)) return;
      if (anchorElRef.current?.contains(t)) return;
      setMenu(null);
    };
    const onScroll = () => setMenu(null);
    document.addEventListener("mousedown", onDocMouseDown);
    listRef.current?.addEventListener("scroll", onScroll);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      listRef.current?.removeEventListener("scroll", onScroll);
    };
  }, [menu]);

  // Qidiruv ikonkasi bosilganda: panelni ochib, qidiruv maydoniga fokus beramiz
  const openAndSearch = () => {
    setOpen(true);
    setTimeout(() => searchRef.current?.focus(), 80);
  };

  // Pin qilinganlar alohida bo'lim (chats allaqachon pin-birinchi tartibda keladi)
  const pinnedChats = chats.filter((c) => c.pinned);
  const recentChats = chats.filter((c) => !c.pinned);

  return (
    <aside
      className={styles.aside}
      style={{
        flex: `0 0 ${open ? SW : COLL}px`,
        width: (open ? SW : COLL) + "px",
        background: side.bg,
        color: side.fg,
        borderRight: "1px solid " + side.border,
      }}
    >
      {!open ? (
        // yig'ilgan (collapsed) rail
        <div className={styles.rail}>
          {/* Ochish/yopish tugmasi endi tashqarida (SidebarToggle) — bu yerda
              faqat statik brend belgisi, asosiy header bilan balandligi bir xil */}
          <div className={styles.railHead} style={{ borderBottom: "1px solid " + side.border }}>
            <span style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 36, height: 36, borderRadius: 10, color: PRIMARY, background: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,.18)" }}>
              <Logo size={22} />
            </span>
          </div>
          <HButton onClick={newChat} data-tip="Yangi suhbat" aria-label="Yangi suhbat boshlash" className={`${styles.railBtn} tip-right`} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
          </HButton>
          <HButton onClick={openAndSearch} data-tip="Qidirish" aria-label="Suhbatlardan qidirish" className={`${styles.railBtn} tip-right`} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
          </HButton>
          <HButton onClick={() => setOpen(true)} data-tip="Tarix" aria-label="Suhbatlar tarixi" className={`${styles.railBtn} tip-right`} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><line x1="8" y1="7" x2="20" y2="7" /><line x1="8" y1="12" x2="20" y2="12" /><line x1="8" y1="17" x2="20" y2="17" /><circle cx="4" cy="7" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="17" r="1" /></svg>
          </HButton>
          <div className={styles.railSpacer} />
          <HButton
            onClick={openProfile}
            data-tip={userName}
            aria-label={userName}
            className={`${styles.railBtn} tip-right`}
            baseStyle={{ opacity: 0.95, color: side.fg }}
            hoverStyle={sideHover}
          >
          <div className={styles.avatarSm}>{initial}</div>
          </HButton>
        </div>
      ) : (
        // ochiq panel
        <div className={styles.panel}>
          <div className={styles.panelHead} style={{ borderBottom: "1px solid " + side.border }}>
            <div className={styles.panelHeadBrand}>
              <div className={styles.logoIcon} style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 38, height: 38, borderRadius: 10, color: PRIMARY, background: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,.18)" }}><Logo size={24} /></div>
              <div className={styles.brandText} style={{ color: side.fg }}>
                Turon<span className={styles.brandTextAi}> AI</span>
              </div>
            </div>
          </div>

          <div className={styles.newChatRow}>
            <HButton onClick={newChat} className={styles.newChatBtn} baseStyle={{ border: "1px solid " + side.border, background: side.btn, color: side.fg }} hoverStyle={{ ...btnHover, transform: "translateY(-2px)", boxShadow: "0 6px 16px rgba(0,0,0,.18)" }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              <span>{newChatLabel}</span>
            </HButton>
          </div>

          {/* Suhbatlar tarixi bo'yicha jonli qidiruv */}
          <div className={styles.searchRow}>
            <svg className={styles.searchIcon} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className={styles.searchInput}
              style={{ color: side.fg }}
            />
            {search && (
              <button onClick={() => setSearch("")} data-tip="Tozalash" aria-label="Tozalash" className={styles.searchClear}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
              </button>
            )}
          </div>

          <div className={styles.chatList} ref={listRef}>
            {chats.length === 0 && (
              <div className={styles.noResults} style={{ color: side.sub }}>{noResultsLabel}</div>
            )}
            {pinnedChats.length > 0 && (
              <div className={styles.sectionLabel} style={{ color: side.sub }}>{pinnedSectionLabel}</div>
            )}
            <div className={styles.chatGroupItems}>
              {pinnedChats.map((c) => renderRow(c))}
            </div>
            {pinnedChats.length > 0 && recentChats.length > 0 && (
              <div className={styles.sectionLabel} style={{ color: side.sub }}>{recentsSectionLabel}</div>
            )}
            <div className={styles.chatGroupItems}>
              {recentChats.map((c) => renderRow(c))}
            </div>
          </div>

          <HButton onClick={openProfile} className={styles.profileTrigger} baseStyle={{ borderTop: "1px solid " + side.border, color: side.fg }} hoverStyle={{ background: "rgba(255,255,255,.07)" }}>
            <div className={styles.avatarSm}>{initial}</div>
            <div className={styles.profileMeta}>
              <div className={styles.profileName}>{userName}</div>
              <div className={styles.profileHandle} style={{ color: side.sub }}>{userHandle}</div>
            </div>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={styles.chevron}><polyline points="9 18 15 12 9 6" /></svg>
          </HButton>
        </div>
      )}
    </aside>
  );

  function renderRow(c: Chat) {
    const act = c.id === activeId;
    const menuOpen = menu?.id === c.id;
    const rowVars = { "--row-hover-bg": side.active } as CSSProperties;
    return (
      // Qator: butun fon (tanlash tugmasi + "..." tugmasi) birgalikda bitta
      // yaxlit kartani hosil qiladi — ikkisi alohida <button>, bosish
      // hodisalari aralashmasin deb.
      <div
        key={c.id}
        className={styles.chatRow}
        style={{ background: act ? side.active : undefined, ...rowVars }}
      >
        <HButton
          onClick={() => setActiveId(c.id)}
          aria-current={act ? "true" : undefined}
          className={styles.chatItem}
          baseStyle={{ color: side.fg }}
          hoverStyle={{ transform: "translateX(3px)" }}
        >
          <span className={styles.chatDot} style={{ background: act ? side.logo : "transparent" }} />
          <span className={styles.chatTitle}>{c.title || newChatLabel}</span>
        </HButton>
        <button
          onClick={(e) => openMenu(e, c.id)}
          data-tip={moreOptionsLabel}
          aria-label={moreOptionsLabel}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          className={`${styles.moreBtn} ${menuOpen ? styles.moreBtnActive : ""}`}
        >
          <RiMore2Fill size={15} />
        </button>
        {menuOpen &&
          createPortal(
            <div
              ref={menuRef}
              role="menu"
              className={styles.moreMenu}
              style={{ top: menu.top, left: menu.left, width: MENU_W }}
            >
              <div className={styles.moreMenuTime}>{formatLastMessageTime(c.lastMessageAt, todayLabel)}</div>
              <button
                role="menuitem"
                className={styles.moreMenuItem}
                onClick={(e) => {
                  e.stopPropagation();
                  onTogglePin(c.id);
                  setMenu(null);
                }}
              >
                {c.pinned ? <RiPushpin2Line size={15} /> : <RiPushpin2Fill size={15} />}
                <span>{c.pinned ? unpinChatLabel : pinChatLabel}</span>
              </button>
              <button
                role="menuitem"
                className={`${styles.moreMenuItem} ${styles.moreMenuItemDanger}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveChat(c.id);
                  setMenu(null);
                }}
              >
                <RiDeleteBin5Fill size={15} />
                <span>{removeChatLabel}</span>
              </button>
            </div>,
            document.body
          )}
      </div>
    );
  }
}

export { SW, COLL };
