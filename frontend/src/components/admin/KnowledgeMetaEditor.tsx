import { useState } from "react";
import FilterSelect from "./FilterSelect";
import {
  KNOWLEDGE_CATEGORIES,
  setKnowledgeMeta,
  type KnowledgeCategory,
} from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./KnowledgeMetaEditor.module.css";

interface Props {
  title: string;
  // Admin qo'ygan turkum ("" — qo'yilmagan, bot o'zi aniqlaydi)
  category: KnowledgeCategory | "";
  // Bot aniqlagan turkum — "Avtomatik (…)" variantida ko'rsatiladi
  autoCategory: KnowledgeCategory;
  note: string;
  t: AdminStrings;
  onSaved: () => void;
}

// Hujjat sahifasidagi "Turkum va izoh": hujjat nimaga tegishli ekanini
// belgilash (kredit, omonat, ...) — ro'yxat filtri va bot katalogi shuni ishlatadi.
export default function KnowledgeMetaEditor({ title, category, autoCategory, note, t: admin, onSaved }: Props) {
  const [cat, setCat] = useState<KnowledgeCategory | "">(category);
  const [text, setText] = useState(note);
  const [saved, setSaved] = useState({ cat: category, text: note });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const names = admin.knowledgeCategoryNames;
  const dirty = cat !== saved.cat || text.trim() !== saved.text.trim();

  const save = async () => {
    setBusy(true);
    setErr(null);
    setOk(false);
    try {
      await setKnowledgeMeta(title, cat || null, text);
      setSaved({ cat, text: text.trim() });
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
      <div className={styles.row}>
        <FilterSelect
          value={cat}
          onChange={(v) => {
            setCat(v as KnowledgeCategory | "");
            setOk(false);
          }}
          options={[
            { value: "", label: admin.knowledgeCategoryAuto(names[autoCategory]) },
            ...KNOWLEDGE_CATEGORIES.map((c) => ({ value: c, label: names[c] })),
          ]}
        />
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
