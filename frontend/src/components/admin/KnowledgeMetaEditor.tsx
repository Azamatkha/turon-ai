import { useState } from "react";
import {
  AUDIENCES,
  createCategory,
  setKnowledgeMeta,
  type Audience,
  type KbCategory,
} from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./KnowledgeMetaEditor.module.css";

interface Props {
  title: string;
  // Admin qo'ygan turkumlar kalitlari (bo'sh — "Turkumsiz")
  categories: string[];
  // Admin yaratgan turkumlar ro'yxati
  allCategories: KbCategory[];
  audience: Audience | "";
  note: string;
  t: AdminStrings;
  onSaved: () => void;
}

const sameSet = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

// Hujjat sahifasidagi "Turkum, mijoz turi va izoh". Hujjat bir NECHTA turkumda
// bo'lishi mumkin (masalan Avtokredit — Kreditlar ham, Avtokreditlar ham).
// Mos turkum bo'lmasa shu yerning o'zida yangisini qo'shish mumkin.
export default function KnowledgeMetaEditor({
  title,
  categories,
  allCategories,
  audience,
  note,
  t: admin,
  onSaved,
}: Props) {
  const [cats, setCats] = useState<string[]>(categories);
  const [aud, setAud] = useState<Audience | "">(audience);
  const [text, setText] = useState(note);
  const [saved, setSaved] = useState({ cats: categories, aud: audience, text: note });
  // Shu yerda yaratilgan turkumlar — ro'yxat qayta yuklanguncha ham ko'rinsin
  const [extra, setExtra] = useState<KbCategory[]>([]);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const options = [...allCategories, ...extra.filter((e) => !allCategories.some((c) => c.key === e.key))];
  const dirty = !sameSet(cats, saved.cats) || aud !== saved.aud || text.trim() !== saved.text.trim();

  const toggle = (key: string) => {
    setOk(false);
    setCats((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };

  const addCategory = async () => {
    const name = newName.trim();
    if (!name) return;
    setBusy(true);
    setErr(null);
    try {
      const cat = await createCategory({ name, keywords: [] });
      setExtra((prev) => [...prev, cat]);
      setCats((prev) => [...prev, cat.key]);
      setNewName("");
      setAdding(false);
      setOk(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setErr(null);
    setOk(false);
    try {
      await setKnowledgeMeta(title, cats, aud || null, text);
      setSaved({ cats, aud, text: text.trim() });
      setText(text.trim());
      setOk(true);
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.box}>
      <div className={styles.label}>{admin.knowledgeCategoryLabel}</div>

      <div className={styles.sub}>{admin.knowledgeCategoriesPick}</div>
      <div className={styles.chips}>
        {options.map((c) => {
          const on = cats.includes(c.key);
          return (
            <button
              key={c.key}
              type="button"
              className={`${styles.chip} ${on ? styles.chipOn : ""}`}
              aria-pressed={on}
              onClick={() => toggle(c.key)}
              disabled={busy}
            >
              {on ? "✓ " : ""}
              {c.name}
            </button>
          );
        })}
        {adding ? (
          <span className={styles.newRow}>
            <input
              className={styles.newInput}
              value={newName}
              maxLength={100}
              autoFocus
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void addCategory();
                if (e.key === "Escape") setAdding(false);
              }}
              placeholder={admin.knowledgeCategoryNewPh}
              aria-label={admin.knowledgeCategoryNewPh}
            />
            <button type="button" className={styles.newBtn} onClick={() => void addCategory()} disabled={busy || !newName.trim()}>
              {admin.knowledgeCategoryCreate}
            </button>
            <button type="button" className={styles.linkBtn} onClick={() => setAdding(false)} disabled={busy}>
              {admin.knowledgeBulkCancel}
            </button>
          </span>
        ) : (
          <button type="button" className={`${styles.chip} ${styles.chipNew}`} onClick={() => setAdding(true)} disabled={busy}>
            {admin.knowledgeCategoryNew}
          </button>
        )}
      </div>

      <div className={styles.sub}>{admin.knowledgeAudienceLabel}</div>
      <div className={styles.chips} role="radiogroup" aria-label={admin.knowledgeAudienceLabel}>
        {(["", ...AUDIENCES] as const).map((a) => (
          <button
            key={a || "none"}
            type="button"
            role="radio"
            aria-checked={aud === a}
            className={`${styles.chip} ${aud === a ? styles.chipOn : ""}`}
            onClick={() => {
              setAud(a);
              setOk(false);
            }}
            disabled={busy}
          >
            {admin.knowledgeAudience[a || "none"]}
          </button>
        ))}
      </div>

      <div className={styles.sub}>{admin.knowledgeNoteLabel}</div>
      <div className={styles.row}>
        <input
          className={styles.note}
          value={text}
          maxLength={500}
          onChange={(e) => {
            setText(e.target.value);
            setOk(false);
          }}
          placeholder={admin.knowledgeNotePh}
          aria-label={admin.knowledgeNoteLabel}
        />
        <button type="button" className={styles.saveBtn} onClick={() => void save()} disabled={busy || !dirty}>
          {admin.knowledgeMetaSave}
        </button>
        {ok && <span className={styles.ok} role="status">{admin.knowledgeMetaSaved}</span>}
      </div>
      {err && <div className={styles.err}>{err}</div>}
      <p className={styles.hint}>{admin.knowledgeMetaHint}</p>
    </div>
  );
}
