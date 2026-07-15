import { useEffect, useRef, useState } from "react";
import HButton from "../common/HButton";
import type { AdminStrings } from "../../types/i18n";
import { listKnowledge, uploadEmployees, uploadEmployeesJson, type KnowledgeItem } from "../../services/knowledgeService";
import KnowledgeDetailView from "./KnowledgeDetailView";
import styles from "./KnowledgeListView.module.css";

interface KnowledgeListViewProps {
  mounted: boolean;
  t: AdminStrings;
  onAddClick: () => void;
}

// Vektor bazaga yuklangan ma'lumotlar ro'yxati (sarlavha bo'yicha guruhlangan).
type SortKey = "title" | "chunks";

export default function KnowledgeListView({ mounted, t: admin, onAddClick }: KnowledgeListViewProps) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("title");
  const fileRef = useRef<HTMLInputElement>(null);
  const [empUploading, setEmpUploading] = useState(false);
  const [empMsg, setEmpMsg] = useState<string | null>(null);

  // Xodimlar Excel (.xlsx) faylini yuklash — backend har xodimni Qdrant'ga yozadi
  const onEmployeesPicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // bir xil faylni qayta tanlash mumkin bo'lsin
    if (!file) return;
    setEmpUploading(true);
    setEmpMsg(null);
    try {
      const isJson = file.name.toLowerCase().endsWith(".json");
      let res;
      if (isJson) {
        const parsed = JSON.parse(await file.text());
        const records = Array.isArray(parsed) ? parsed : parsed.employees;
        if (!Array.isArray(records)) throw new Error("JSON massiv bo'lishi kerak");
        res = await uploadEmployeesJson(records);
      } else {
        res = await uploadEmployees(file);
      }
      setEmpMsg(admin.knowledgeEmployeesResult(res.chunks));
      await load();
    } catch (err) {
      setEmpMsg(err instanceof Error ? err.message : admin.knowledgeEmployeesError);
    } finally {
      setEmpUploading(false);
    }
  };

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
        t={admin}
      />
    );
  }

  const q = search.trim().toLowerCase();
  const visible = items
    .filter((it) => !q || it.title.toLowerCase().includes(q) || it.preview.toLowerCase().includes(q))
    .sort((a, b) =>
      sortKey === "chunks" ? b.chunks - a.chunks : a.title.localeCompare(b.title)
    );

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      <div className={styles.head}>
        <div className={styles.count}>
          {!loading && !err ? admin.knowledgeItemsCount(items.length) : ""}
        </div>
        <div className={styles.headActions}>
          <HButton
            onClick={onAddClick}
            className={styles.addBtn}
            baseStyle={{}}
            hoverStyle={{ transform: "translateY(-1px)", boxShadow: "0 8px 20px rgba(23, 63, 115,.28)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.1" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            {admin.knowledgeAdd}
          </HButton>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.json"
            style={{ display: "none" }}
            onChange={onEmployeesPicked}
          />
          <HButton
            onClick={() => fileRef.current?.click()}
            className={styles.reloadBtn}
            baseStyle={{ opacity: empUploading ? 0.6 : 1 }}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
            {empUploading ? "…" : admin.knowledgeEmployees}
          </HButton>
          <HButton
            onClick={load}
            className={styles.reloadBtn}
            baseStyle={{}}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
            {admin.knowledgeReload}
          </HButton>
        </div>
      </div>

      {empMsg && (
        <div className={styles.empBanner} onClick={() => setEmpMsg(null)}>{empMsg}</div>
      )}

      {!loading && !err && items.length > 0 && (
        <div className={styles.toolbar}>
          <input
            className={styles.searchInput}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={admin.knowledgeSearchPh}
          />
          <select
            className={styles.sortSelect}
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
          >
            <option value="title">{admin.knowledgeSortTitle}</option>
            <option value="chunks">{admin.knowledgeSortChunks}</option>
          </select>
        </div>
      )}

      {loading ? (
        <div className={styles.state}>
          <span className={styles.spinner} />
        </div>
      ) : err ? (
        <div className={styles.errMsg}>{err}</div>
      ) : items.length === 0 ? (
        <div className={styles.empty}>{admin.knowledgeEmpty}</div>
      ) : visible.length === 0 ? (
        <div className={styles.empty}>{admin.knowledgeNoResults}</div>
      ) : (
        <div className={styles.list}>
          {visible.map((it) => (
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
