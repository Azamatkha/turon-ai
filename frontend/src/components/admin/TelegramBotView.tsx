import { useCallback, useEffect, useState } from "react";
import TelegramBotChatModal from "./TelegramBotChatModal";
import FilterSelect from "./FilterSelect";
import {
  listTgUsers,
  type ApiTgUser,
  type TgUserFilter,
  type TgUserSort,
} from "../../services/telegramBotService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./TelegramBotView.module.css";

interface TelegramBotViewProps {
  mounted: boolean;
  t: AdminStrings;
}

// Bir sahifadagi userlar soni (sahifalash backendda)
const PAGE_SIZE = 20;

const LANG_FLAG: Record<string, string> = { uz: "🇺🇿", ru: "🇷🇺", en: "🇬🇧" };

export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function tgUserName(u: ApiTgUser): string {
  return u.full_name || (u.username ? `@${u.username}` : String(u.telegram_id));
}

/** Ko'rsatiladigan sahifa raqamlari: 1 … 4 5 6 … 12 (null = "…"). */
function pageList(current: number, total: number): (number | null)[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const out: (number | null)[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push(null);
    out.push(p);
  });
  return out;
}

// Telegram yordam boti userlari. Ma'lumotni bot o'zi davriy yuboradi — bu yerda faqat o'qish.
export default function TelegramBotView({ mounted, t: admin }: TelegramBotViewProps) {
  const [items, setItems] = useState<ApiTgUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<TgUserFilter>("");
  const [sort, setSort] = useState<TgUserSort>("joined");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApiTgUser | null>(null);

  // Qidiruv har harfda so'rov yubormasin — 350ms kutamiz, natija 1-sahifadan
  useEffect(() => {
    const id = window.setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(id);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTgUsers({ search: query, page, size: PAGE_SIZE, status, sort });
      setItems(data.items);
      setTotal(data.total);
      setErr(null);
    } catch (e) {
      setItems([]);
      setTotal(0);
      setErr((e instanceof Error && e.message) || admin.tgBotLoadError);
    } finally {
      setLoading(false);
    }
  }, [query, page, status, sort, admin.tgBotLoadError]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;

  return (
    <div className={mounted ? `${styles.wrap} ${styles.in}` : styles.wrap}>
      <div className={styles.toolbar}>
        <input
          className={styles.search}
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={admin.tgBotSearchPh}
          aria-label={admin.tgBotSearchPh}
        />
        <FilterSelect
          value={status}
          onChange={(v) => {
            setStatus(v as TgUserFilter);
            setPage(1);
          }}
          options={[
            { value: "", label: admin.tgBotFilterAll },
            { value: "pending", label: admin.tgBotFilterPending },
            { value: "registered", label: admin.tgBotFilterRegistered },
            { value: "unregistered", label: admin.tgBotNotRegistered },
            { value: "banned", label: admin.tgBotBanned },
          ]}
        />
        <FilterSelect
          value={sort}
          onChange={(v) => {
            setSort(v as TgUserSort);
            setPage(1);
          }}
          options={[
            { value: "joined", label: admin.tgBotSortJoined },
            { value: "last_message", label: admin.tgBotSortLast },
          ]}
        />
        <button type="button" className={styles.refreshBtn} onClick={() => void load()} disabled={loading}>
          {admin.faceLogsRefresh}
        </button>
        <span className={styles.total}>{admin.faceLogsTotal(total)}</span>
      </div>

      {err && <div className={styles.error}>{err}</div>}

      <div className={styles.card}>
        <div className={`${styles.row} ${styles.headRow}`}>
          <span>{admin.tgBotColUser}</span>
          <span>{admin.tgBotColPhone}</span>
          <span>{admin.tgBotColLang}</span>
          <span>{admin.tgBotColMessages}</span>
          <span>{admin.tgBotColJoined}</span>
          <span>{admin.tgBotColLast}</span>
        </div>

        {!loading && items.length === 0 && !err && <div className={styles.empty}>{admin.tgBotEmpty}</div>}

        {items.map((u) => (
          <button
            key={u.id}
            type="button"
            className={`${styles.row} ${styles.dataRow}`}
            onClick={() => setSelected(u)}
          >
            <span className={styles.colUser}>
              <span className={styles.name}>
                {tgUserName(u)}
                {u.is_banned && <span className={`${styles.badge} ${styles.banned}`}>{admin.tgBotBanned}</span>}
              </span>
              <span className={styles.sub}>
                {u.username ? `@${u.username} · ` : ""}
                {u.telegram_id}
                {u.reg_step !== "done" && ` · ${admin.tgBotNotRegistered}`}
              </span>
            </span>
            <span className={styles.colMuted}>{u.phone || "—"}</span>
            <span className={styles.colMuted}>
              {u.language ? `${LANG_FLAG[u.language] ?? ""} ${u.language}` : "—"}
            </span>
            <span className={styles.colCount}>
              {u.messages_count}
              {u.pending_count > 0 && (
                <span className={`${styles.badge} ${styles.pending}`}>{admin.tgBotPending(u.pending_count)}</span>
              )}
            </span>
            <span className={styles.colMuted}>{fmtDate(u.first_seen_at)}</span>
            <span className={styles.colMuted}>{fmtDate(u.last_message_at)}</span>
          </button>
        ))}

        {total > PAGE_SIZE && (
          <nav className={styles.pager} aria-label={admin.pageRange(start + 1, start + items.length, total)}>
            <span className={styles.pagerInfo}>{admin.pageRange(start + 1, start + items.length, total)}</span>
            <div className={styles.pagerBtns}>
              <button type="button" className={styles.pageBtn} onClick={() => setPage(page - 1)} disabled={page === 1 || loading} aria-label={admin.pagePrev}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              {pageList(page, totalPages).map((p, i) =>
                p === null ? (
                  <span key={`gap-${i}`} className={styles.pageGap}>…</span>
                ) : (
                  <button key={p} type="button" className={`${styles.pageBtn} ${p === page ? styles.pageBtnActive : ""}`} onClick={() => setPage(p)} disabled={loading} aria-current={p === page ? "page" : undefined}>
                    {p}
                  </button>
                )
              )}
              <button type="button" className={styles.pageBtn} onClick={() => setPage(page + 1)} disabled={page === totalPages || loading} aria-label={admin.pageNext}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
              </button>
            </div>
          </nav>
        )}
      </div>

      {selected && <TelegramBotChatModal user={selected} t={admin} onClose={() => setSelected(null)} />}
    </div>
  );
}
