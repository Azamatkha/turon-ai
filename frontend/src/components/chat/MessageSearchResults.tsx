import { useEffect, useState } from "react";
import { searchMessages, type MessageSearchHit } from "../../services/chatHistoryService";
import type { SideTokens } from "../../types/chat";
import styles from "./MessageSearchResults.module.css";

interface Props {
  query: string;
  // Sarlavha bo'yicha topilgan suhbatlar soni — ikkalasi ham bo'sh bo'lsa
  // umumiy "topilmadi" yozuvi shu yerda chiqadi
  titleMatches: number;
  side: SideTokens;
  label: string;
  noResultsLabel: string;
  onOpen: (sessionId: string) => void;
}

const MIN_LEN = 2;
const DEBOUNCE_MS = 300;

// Matndagi so'rovni ajratib ko'rsatadi (katta-kichik harfsiz). Kirill/lotin
// moslikni backend topadi — bu yerda faqat yozilgan ko'rinishi belgilanadi.
function highlight(text: string, q: string) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark className={styles.mark}>{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </>
  );
}

// Sidebar qidiruvi: sarlavhalardan tashqari xabarlar MATNIDAN ham qidiradi.
export default function MessageSearchResults({ query, titleMatches, side, label, noResultsLabel, onOpen }: Props) {
  const q = query.trim();
  const [hits, setHits] = useState<MessageSearchHit[] | null>(null);

  useEffect(() => {
    if (q.length < MIN_LEN) {
      setHits(null);
      return;
    }
    let alive = true;
    const id = window.setTimeout(() => {
      searchMessages(q)
        .then((h) => alive && setHits(h))
        .catch(() => alive && setHits([]));
    }, DEBOUNCE_MS);
    return () => {
      alive = false;
      window.clearTimeout(id);
    };
  }, [q]);

  if (q.length < MIN_LEN) return null;
  if (hits === null) {
    return <div className={styles.loading} style={{ color: side.sub }}>…</div>;
  }
  if (hits.length === 0) {
    return titleMatches === 0 ? (
      <div className={styles.empty} style={{ color: side.sub }}>{noResultsLabel}</div>
    ) : null;
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.label} style={{ color: side.sub }}>{label}</div>
      {hits.map((h) => (
        <button
          key={h.message_id}
          type="button"
          className={styles.hit}
          style={{ color: side.fg }}
          onClick={() => onOpen(h.session_id)}
        >
          <span className={styles.title}>{h.session_title || "—"}</span>
          <span className={styles.snippet} style={{ color: side.sub }}>{highlight(h.snippet, q)}</span>
        </button>
      ))}
    </div>
  );
}
