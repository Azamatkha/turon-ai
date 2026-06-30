import { CSSProperties, useRef } from "react";
import HButton from "../common/HButton";
import Logo from "../common/Logo";
import type { Chat, SideTokens } from "../../types/chat";
import styles from "./Sidebar.module.css";

const SW = 282;
const COLL = 72;

interface ChatGroup {
  label: string;
  items: Chat[];
}

interface SidebarProps {
  open: boolean;
  setOpen: (v: boolean) => void;
  newChat: () => void;
  newChatLabel: string;
  groups: ChatGroup[];
  activeId: string;
  setActiveId: (id: string) => void;
  onRemoveChat: (id: string) => void;
  removeChatLabel: string;
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

export default function Sidebar({
  open, setOpen, newChat, newChatLabel, groups, activeId, setActiveId, onRemoveChat, removeChatLabel,
  search, setSearch, searchPlaceholder, noResultsLabel,
  side, userName, userHandle, initial, openProfile,
}: SidebarProps) {
  const sideHover: CSSProperties = { background: "rgba(255,255,255,.08)" };
  const btnHover: CSSProperties = { background: "rgba(255,255,255,.13)" };
  const searchRef = useRef<HTMLInputElement>(null);

  // Qidiruv ikonkasi bosilganda: panelni ochib, qidiruv maydoniga fokus beramiz
  const openAndSearch = () => {
    setOpen(true);
    setTimeout(() => searchRef.current?.focus(), 80);
  };

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
          <div className={styles.railHead} style={{ borderBottom: "1px solid " + side.border, color: side.logo }}>
            <Logo size={24} />
          </div>
          <HButton onClick={newChat} title="Yangi suhbat" aria-label="Yangi suhbat boshlash" className={styles.railBtn} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
          </HButton>
          <HButton onClick={openAndSearch} title="Qidirish" aria-label="Suhbatlardan qidirish" className={styles.railBtn} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
          </HButton>
          <HButton onClick={() => setOpen(true)} title="Tarix" aria-label="Suhbatlar tarixi" className={styles.railBtn} baseStyle={{ opacity: 0.82, color: side.fg }} hoverStyle={sideHover}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><line x1="8" y1="7" x2="20" y2="7" /><line x1="8" y1="12" x2="20" y2="12" /><line x1="8" y1="17" x2="20" y2="17" /><circle cx="4" cy="7" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="17" r="1" /></svg>
          </HButton>
          <div className={styles.railSpacer} />
          <HButton
            onClick={openProfile}
            title={userName}
            aria-label={userName}
            className={styles.railBtn}
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
              <div className={styles.logoIcon} style={{ color: side.logo }}><Logo size={26} /></div>
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
              <button onClick={() => setSearch("")} title="Tozalash" aria-label="Tozalash" className={styles.searchClear}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
              </button>
            )}
          </div>

          <div className={styles.chatList}>
            {groups.length === 0 && (
              <div className={styles.noResults} style={{ color: side.sub }}>{noResultsLabel}</div>
            )}
            {groups.map((g) => (
              <div key={g.label}>
                <div className={styles.groupLabel} style={{ color: side.sub }}>{g.label}</div>
                <div className={styles.chatGroupItems}>
                  {g.items.map((c) => {
                    const act = c.id === activeId;
                    return (
                      // Qator: chap tomonda tanlash tugmasi, o'ngda — o'chirish ikonkasi.
                      // Ikkisi alohida <button>, shuning uchun bosish hodisalari aralashmaydi.
                      <div key={c.id} className={styles.chatRow}>
                        <HButton
                          onClick={() => setActiveId(c.id)}
                          aria-current={act ? "true" : undefined}
                          className={styles.chatItem}
                          baseStyle={{ background: act ? side.active : "transparent", color: side.fg }}
                          hoverStyle={{ background: side.active, transform: "translateX(3px)" }}
                        >
                          <span className={styles.chatDot} style={{ background: act ? side.logo : "transparent" }} />
                          <span className={styles.chatTitle}>{c.title || newChatLabel}</span>
                        </HButton>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onRemoveChat(c.id);
                          }}
                          title={removeChatLabel}
                          aria-label={removeChatLabel}
                          className={styles.removeBtn}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                            <path d="M10 11v6M14 11v6" />
                          </svg>
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
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
}

export { SW, COLL };
