import { useEffect, useRef, useState } from "react";
import HButton from "../common/HButton";
import FilterSelect from "./FilterSelect";
import type { AdminStrings } from "../../types/i18n";
import {
  AUDIENCES,
  createCategory,
  deleteKnowledgeBulk,
  employeeStats,
  listCategories,
  listKnowledge,
  setKnowledgeBulk,
  uploadEmployees,
  uploadEmployeesJson,
  type Audience,
  type KbCategory,
  type KnowledgeItem,
} from "../../services/knowledgeService";
import KnowledgeCategoriesModal from "./KnowledgeCategoriesModal";
import KnowledgeDetailView from "./KnowledgeDetailView";
import RescrapePanel from "./RescrapePanel";
import { fmtIsoDate, validityState } from "../../utils/knowledgeValidity";
import styles from "./KnowledgeListView.module.css";

interface KnowledgeListViewProps {
  mounted: boolean;
  t: AdminStrings;
  onAddClick: () => void;
}

// Vektor bazaga yuklangan ma'lumotlar ro'yxati (sarlavha bo'yicha guruhlangan).
type SortKey = "title" | "chunks" | "newest" | "oldest";
// Belgilanganlar bilan nima qilinadi
type BulkAction = "add" | "remove" | "audience" | "delete";

// Filtrlarda "turkumsiz" / "belgilanmagan" qiymati
const NONE = "__none__";
// Ommaviy turkum qo'shishda — "yangi turkum yaratish" varianti
const NEW_CAT = "__new__";

// Sanani solishtirish uchun xavfsiz son (bo'sh/noto'g'ri sana -> 0).
// Eski yozuvlarda `uploaded_at` bo'lmasligi mumkin — ular oxirida turadi.
const ts = (v?: string): number => {
  if (!v) return 0;
  const t = new Date(v).getTime();
  return Number.isNaN(t) ? 0 : t;
};

export default function KnowledgeListView({ mounted, t: admin, onAddClick }: KnowledgeListViewProps) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("title");
  // Faqat muddati o'tgan / yaqinlashgan hujjatlar
  const [onlyStale, setOnlyStale] = useState(false);
  // Turkum filtri: "" — hammasi, NONE — turkumsiz, aks holda turkum kaliti.
  // Turkumni faqat admin qo'yadi (avtomatik taxmin yo'q).
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<KbCategory[]>([]);
  const [catsOpen, setCatsOpen] = useState(false);
  // Mijoz turi filtri: "" — hammasi, NONE — belgilanmagan
  const [audFilter, setAudFilter] = useState("");
  // Belgilash rejimi: bir nechta hujjatga birdaniga turkum / mijoz turi
  // qo'yish yoki ularni bittada o'chirish
  const [selecting, setSelecting] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState<BulkAction>("add");
  const [bulkValue, setBulkValue] = useState("");
  const [bulkNewName, setBulkNewName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);
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

  // Diagnostika: bazada nechta xodim borligini ko'rsatadi (API'ni chaqirmasdan)
  const checkStats = async () => {
    setEmpUploading(true);
    setEmpMsg(null);
    try {
      const s = await employeeStats();
      const depts = Object.entries(s.departments)
        .map(([d, n]) => `${d} (${n})`)
        .join(", ");
      const smp = s.sample
        ? ` · Namuna: ${s.sample.fish ?? "?"} — IP: ${s.sample.ip ?? "?"} (doc_type: ${s.sample.doc_type ?? "?"})`
        : "";
      setEmpMsg(
        `Bazada ${s.employee_count} ta xodim (jami ${s.total_points} nuqta).` +
          (depts ? ` Bo'limlar: ${depts}.` : "") +
          smp
      );
    } catch (err) {
      setEmpMsg(err instanceof Error ? err.message : "Tekshirishda xatolik");
    } finally {
      setEmpUploading(false);
    }
  };

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const [list, cats] = await Promise.all([listKnowledge(), listCategories()]);
      setItems(list);
      setCategories(cats);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeLoadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Muddati o'tgan yoki 7 kun ichida tugaydiganlar
  const isStale = (it: KnowledgeItem) => {
    const st = validityState(it.valid_until);
    return st === "expired" || st === "soon";
  };
  const staleCount = items.filter(isStale).length;

  // Ma'lumot tanlansa — to'liq sahifa (modal emas)
  if (selected) {
    const sel = items.find((i) => i.title === selected);
    return (
      <KnowledgeDetailView
        title={selected}
        validUntil={sel?.valid_until ?? ""}
        itemCategories={(sel?.categories ?? []).filter((k) => categories.some((c) => c.key === k))}
        categories={categories}
        audience={sel?.audience ?? ""}
        note={sel?.note ?? ""}
        onBack={() => setSelected(null)}
        onChanged={load}
        t={admin}
      />
    );
  }

  const q = search.trim().toLowerCase();
  const names = new Map(categories.map((c) => [c.key, c.name]));
  // Hujjat turkumlari (o'chirilgan turkumlar tashlanadi); bo'sh — "Turkumsiz"
  const catsOf = (it: KnowledgeItem) => (it.categories ?? []).filter((k) => names.has(k));
  // Har turkumda nechta hujjat bor — filtr variantlarida ko'rsatiladi.
  // Bir nechta turkumdagi hujjat har birida sanaladi.
  const catCounts = new Map<string, number>();
  for (const it of items) {
    const own = catsOf(it);
    for (const c of own.length ? own : [NONE]) catCounts.set(c, (catCounts.get(c) ?? 0) + 1);
  }
  const audOf = (it: KnowledgeItem) => it.audience || NONE;
  const audCounts = new Map<string, number>();
  for (const it of items) audCounts.set(audOf(it), (audCounts.get(audOf(it)) ?? 0) + 1);
  const audienceOptions = [
    { value: "", label: admin.knowledgeAudienceAll },
    ...AUDIENCES.map((a) => ({ value: a, label: `${admin.knowledgeAudience[a]} (${audCounts.get(a) ?? 0})` })),
    { value: NONE, label: `${admin.knowledgeAudience.none} (${audCounts.get(NONE) ?? 0})` },
  ];
  const categoryOptions = [
    { value: "", label: `${admin.knowledgeCategoryAll} (${items.length})` },
    { value: NONE, label: `${admin.knowledgeCategoryNone} (${catCounts.get(NONE) ?? 0})` },
    ...categories.map((c) => ({ value: c.key, label: `${c.name} (${catCounts.get(c.key) ?? 0})` })),
  ];
  const visible = items
    .filter(
      (it) =>
        !q ||
        it.title.toLowerCase().includes(q) ||
        it.preview.toLowerCase().includes(q) ||
        (it.note ?? "").toLowerCase().includes(q)
    )
    .filter((it) => {
      if (!category) return true;
      const own = catsOf(it);
      return category === NONE ? own.length === 0 : own.includes(category);
    })
    .filter((it) => !audFilter || audOf(it) === audFilter)
    .filter((it) => !onlyStale || isStale(it))
    .sort((a, b) => {
      if (sortKey === "chunks") return b.chunks - a.chunks;
      if (sortKey === "newest") return ts(b.uploaded_at) - ts(a.uploaded_at);
      if (sortKey === "oldest") return ts(a.uploaded_at) - ts(b.uploaded_at);
      return a.title.localeCompare(b.title);
    });

  const togglePick = (title: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });

  const stopSelecting = () => {
    setSelecting(false);
    setPicked(new Set());
    setBulkValue("");
    setBulkNewName("");
    setConfirmDelete(false);
  };

  // Tanlangan amalga mos variantlar (o'chirishda variant yo'q)
  const bulkOptions =
    bulkAction === "audience"
      ? [
          { value: "", label: admin.knowledgeBulkAudiencePick },
          ...AUDIENCES.map((a) => ({ value: a, label: admin.knowledgeAudience[a] })),
          { value: "none", label: admin.knowledgeAudience.none },
        ]
      : [
          { value: "", label: admin.knowledgeBulkPick },
          ...categories.map((c) => ({ value: c.key, label: c.name })),
          ...(bulkAction === "add" ? [{ value: NEW_CAT, label: admin.knowledgeCategoryNew }] : []),
        ];
  const bulkReady =
    picked.size > 0 &&
    (bulkAction === "delete" || (bulkValue !== "" && (bulkValue !== NEW_CAT || bulkNewName.trim() !== "")));

  const applyBulk = async () => {
    if (!bulkReady) return;
    if (bulkAction === "delete" && !confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setBulkBusy(true);
    const titles = [...picked];
    try {
      if (bulkAction === "delete") {
        await deleteKnowledgeBulk(titles);
        setEmpMsg(admin.knowledgeBulkDeleted(titles.length));
      } else if (bulkAction === "audience") {
        await setKnowledgeBulk(titles, { audience: bulkValue as Audience | "none" });
        setEmpMsg(admin.knowledgeBulkDone(titles.length));
      } else {
        let key = bulkValue;
        if (key === NEW_CAT) key = (await createCategory({ name: bulkNewName.trim(), keywords: [] })).key;
        await setKnowledgeBulk(titles, bulkAction === "add" ? { add: [key] } : { remove: [key] });
        setEmpMsg(admin.knowledgeBulkDone(titles.length));
      }
      stopSelecting();
      await load();
    } catch (e) {
      setEmpMsg(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className={`${styles.wrap} ${mounted ? styles.in : ""}`}>
      {catsOpen && (
        <KnowledgeCategoriesModal
          categories={categories}
          t={admin}
          onClose={() => setCatsOpen(false)}
          onChanged={load}
        />
      )}
      <div className={styles.head}>
        <div className={styles.count}>
          {!loading && !err ? admin.knowledgeItemsCount(items.length) : ""}
        </div>
        <div className={styles.headActions}>
          <HButton
            onClick={onAddClick}
            className={`${styles.addBtn} tu-shiny`}
            baseStyle={{}}
            hoverStyle={{ transform: "translateY(-1px)", boxShadow: "0 8px 20px rgba(25, 48, 112,.28)" }}
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
            className={`${styles.reloadBtn} tu-shiny`}
            baseStyle={{ opacity: empUploading ? 0.6 : 1 }}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
            {empUploading ? "…" : admin.knowledgeEmployees}
          </HButton>
          <HButton
            onClick={checkStats}
            className={`${styles.reloadBtn} tu-shiny`}
            baseStyle={{ opacity: empUploading ? 0.6 : 1 }}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
            {admin.knowledgeEmployeesCheck}
          </HButton>
          <HButton
            onClick={() => setCatsOpen(true)}
            className={`${styles.reloadBtn} tu-shiny`}
            baseStyle={{}}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z" /><circle cx="7.5" cy="7.5" r="1.5" /></svg>
            {admin.knowledgeCategoriesManage}
          </HButton>
          <HButton
            onClick={load}
            className={`${styles.reloadBtn} tu-shiny`}
            baseStyle={{}}
            hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
            {admin.knowledgeReload}
          </HButton>
        </div>
      </div>

      <RescrapePanel t={admin} onFinished={load} />

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
          <FilterSelect value={category} onChange={setCategory} options={categoryOptions} />
          <FilterSelect value={audFilter} onChange={setAudFilter} options={audienceOptions} />
          <FilterSelect
            value={sortKey}
            onChange={(v) => setSortKey(v as SortKey)}
            options={[
              { value: "title", label: admin.knowledgeSortTitle },
              { value: "chunks", label: admin.knowledgeSortChunks },
              { value: "newest", label: admin.knowledgeSortNewest },
              { value: "oldest", label: admin.knowledgeSortOldest },
            ]}
          />
          <button
            type="button"
            className={`${styles.staleBtn} ${styles.selectBtn} ${selecting ? styles.selectBtnOn : ""}`}
            aria-pressed={selecting}
            onClick={() => (selecting ? stopSelecting() : setSelecting(true))}
          >
            {admin.knowledgeSelectMode}
          </button>
          {staleCount > 0 && (
            <button
              type="button"
              className={`${styles.staleBtn} ${onlyStale ? styles.staleBtnOn : ""}`}
              aria-pressed={onlyStale}
              onClick={() => setOnlyStale((v) => !v)}
            >
              {admin.knowledgeValidityFilter(staleCount)}
            </button>
          )}
        </div>
      )}

      {selecting && (
        <div className={styles.bulkBar}>
          <span className={styles.bulkCount}>{admin.knowledgeSelectedCount(picked.size)}</span>
          <button
            type="button"
            className={styles.bulkLink}
            onClick={() => setPicked(new Set(visible.map((it) => it.title)))}
          >
            {admin.knowledgeSelectAllVisible}
          </button>
          <FilterSelect
            value={bulkAction}
            onChange={(v) => {
              setBulkAction(v as BulkAction);
              setBulkValue("");
              setConfirmDelete(false);
            }}
            options={(["add", "remove", "audience", "delete"] as const).map((a) => ({
              value: a,
              label: admin.knowledgeBulkAction[a],
            }))}
          />
          {bulkAction !== "delete" && <FilterSelect value={bulkValue} onChange={setBulkValue} options={bulkOptions} />}
          {bulkValue === NEW_CAT && (
            <input
              className={styles.bulkInput}
              value={bulkNewName}
              maxLength={100}
              autoFocus
              onChange={(e) => setBulkNewName(e.target.value)}
              placeholder={admin.knowledgeCategoryNewPh}
              aria-label={admin.knowledgeCategoryNewPh}
            />
          )}
          {confirmDelete && <span className={styles.bulkWarn}>{admin.knowledgeBulkDeleteConfirm(picked.size)}</span>}
          <button
            type="button"
            className={`${styles.bulkApply} ${bulkAction === "delete" ? styles.bulkDanger : ""}`}
            onClick={() => void applyBulk()}
            disabled={bulkBusy || !bulkReady}
          >
            {bulkAction === "delete"
              ? confirmDelete
                ? admin.knowledgeBulkDeleteYes
                : admin.knowledgeBulkAction.delete
              : admin.knowledgeBulkApply}
          </button>
          <button type="button" className={styles.bulkLink} onClick={stopSelecting} disabled={bulkBusy}>
            {admin.knowledgeBulkCancel}
          </button>
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
              className={`${styles.card} ${selecting && picked.has(it.title) ? styles.cardPicked : ""}`}
              onClick={() => (selecting ? togglePick(it.title) : setSelected(it.title))}
              aria-pressed={selecting ? picked.has(it.title) : undefined}
            >
              <div className={styles.cardTop}>
                {selecting && (
                  <span className={`${styles.check} ${picked.has(it.title) ? styles.checkOn : ""}`} aria-hidden="true">
                    {picked.has(it.title) ? "✓" : ""}
                  </span>
                )}
                <div className={styles.cardTitle}>{it.title}</div>
                <span className={styles.badge}>{admin.knowledgeChunks(it.chunks)}</span>
              </div>
              {it.note && <div className={styles.note}>{it.note}</div>}
              {it.preview && <div className={styles.preview}>{it.preview}…</div>}
              <div className={styles.cardFoot}>
                <span className={styles.lang}>{it.lang.toUpperCase()}</span>
                {/* Turkumlar — to'q rangda, turkumsiz — xira */}
                {catsOf(it).length > 0 ? (
                  catsOf(it).map((k) => (
                    <span key={k} className={`${styles.category} ${styles.categoryManual}`}>
                      {names.get(k)}
                    </span>
                  ))
                ) : (
                  <span className={styles.category}>{admin.knowledgeCategoryNone}</span>
                )}
                {it.audience && <span className={`${styles.category} ${styles.audience}`}>{admin.knowledgeAudience[it.audience]}</span>}
                {it.duplicates && it.duplicates.length > 0 && (
                  <span className={`${styles.validity} ${styles.vSoon}`} title={it.duplicates.join("\n")}>
                    {admin.knowledgeDuplicate(it.duplicates.length)}
                  </span>
                )}
                {it.valid_until && (() => {
                  const st = validityState(it.valid_until);
                  const cls = st === "expired" ? styles.vExpired : st === "soon" ? styles.vSoon : styles.vOk;
                  const label = st === "expired" ? admin.knowledgeValidityExpired : admin.knowledgeValidityUntil;
                  return <span className={`${styles.validity} ${cls}`}>{label} {fmtIsoDate(it.valid_until)}</span>;
                })()}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
