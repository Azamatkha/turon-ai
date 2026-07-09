import { useEffect, useState } from "react";
import HButton from "../common/HButton";
import { admin } from "../../locales";
import { listKnowledge, type KnowledgeItem } from "../../services/knowledgeService";
import KnowledgeDetailView from "./KnowledgeDetailView";
import styles from "./KnowledgeListView.module.css";

interface KnowledgeListViewProps {
  mounted: boolean;
}

// Vektor bazaga yuklangan ma'lumotlar ro'yxati (sarlavha bo'yicha guruhlangan).
export default function KnowledgeListView({ mounted }: KnowledgeListViewProps) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      setItems(await listKnowledge());
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeLoadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Ma'lumot tanlansa — to'liq sahifa (modal emas)
  if (selected) {
    return (
      <KnowledgeDetailView
        title={selected}
        onBack={() => setSelected(null)}
        onChanged={load}
      />
    );
  }

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      <div className={styles.head}>
        <div className={styles.count}>
          {!loading && !err ? admin.knowledgeChunks(items.length).replace(/bo‘lak/, "ma’lumot") : ""}
        </div>
        <HButton
          onClick={load}
          className={styles.reloadBtn}
          baseStyle={{}}
          hoverStyle={{ background: "#e6eae3", color: "#173f73" }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
          {admin.knowledgeReload}
        </HButton>
      </div>

      {loading ? (
        <div className={styles.state}>
          <span className={styles.spinner} />
        </div>
      ) : err ? (
        <div className={styles.errMsg}>{err}</div>
      ) : items.length === 0 ? (
        <div className={styles.empty}>{admin.knowledgeEmpty}</div>
      ) : (
        <div className={styles.list}>
          {items.map((it) => (
            <button
              key={it.title}
              className={styles.card}
              onClick={() => setSelected(it.title)}
            >
              <div className={styles.cardTop}>
                <div className={styles.cardTitle}>{it.title}</div>
                <span className={styles.badge}>{admin.knowledgeChunks(it.chunks)}</span>
              </div>
              {it.preview && <div className={styles.preview}>{it.preview}…</div>}
              <div className={styles.lang}>{it.lang.toUpperCase()}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
