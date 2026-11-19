import { useState } from "react";
import {
  createCategory,
  deleteCategory,
  updateCategory,
  type KbCategory,
} from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import { useModalA11y } from "../../hooks/useModalA11y";
import styles from "./KnowledgeCategoriesModal.module.css";

interface Props {
  categories: KbCategory[];
  t: AdminStrings;
  onClose: () => void;
  // Ro'yxat o'zgardi — ota komponent turkumlar va hujjatlarni qayta yuklaydi
  onChanged: () => void;
}

// "kredit, ipoteka" <-> ["kredit", "ipoteka"]
const splitKeywords = (v: string) =>
  v.split(/[,;\n]/).map((w) => w.trim()).filter(Boolean);

interface RowProps {
  cat: KbCategory;
  t: AdminStrings;
  onChanged: () => void;
}

// Bitta turkum: nomi va kalit so'zlari joyida tahrirlanadi
function CategoryRow({ cat, t: admin, onChanged }: RowProps) {
  const [name, setName] = useState(cat.name);
  const [kw, setKw] = useState(cat.keywords.join(", "));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

  const dirty = name.trim() !== cat.name || kw.trim() !== cat.keywords.join(", ");

  const save = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await updateCategory(cat.key, { name: name.trim(), keywords: splitKeywords(kw) });
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setErr(null);
    try {
      await deleteCategory(cat.key);
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
      setBusy(false);
    }
  };

  return (
    <div className={styles.row}>
      <div className={styles.fields}>
        <input
          className={styles.name}
          value={name}
          maxLength={100}
          onChange={(e) => setName(e.target.value)}
          placeholder={admin.knowledgeCategoryNamePh}
          aria-label={admin.knowledgeCategoryNamePh}
          disabled={busy}
        />
        <input
          className={styles.kw}
          value={kw}
          onChange={(e) => setKw(e.target.value)}
          placeholder={admin.knowledgeCategoryKeywordsPh}
          aria-label={admin.knowledgeCategoryKeywordsPh}
          disabled={busy}
        />
      </div>
      <div className={styles.actions}>
        {confirm ? (
          <>
            <span className={styles.confirmText}>{admin.knowledgeCategoryDeleteConfirm(cat.name)}</span>
            <button type="button" className={styles.dangerBtn} onClick={() => void remove()} disabled={busy}>
              {admin.knowledgeCategoryDelete}
            </button>
            <button type="button" className={styles.ghostBtn} onClick={() => setConfirm(false)} disabled={busy}>
              {admin.knowledgeBulkCancel}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className={styles.saveBtn}
              onClick={() => void save()}
              disabled={busy || !dirty || !name.trim()}
            >
              {admin.knowledgeMetaSave}
            </button>
            <button type="button" className={styles.ghostBtn} onClick={() => setConfirm(true)} disabled={busy}>
              {admin.knowledgeCategoryDelete}
            </button>
          </>
        )}
      </div>
      {err && <div className={styles.err}>{err}</div>}
    </div>
  );
}

// Bilim bazasi turkumlarini boshqarish: admin o'zi qo'shadi, nomini va kalit
// so'zlarini o'zgartiradi, o'chiradi. Bot hech narsani o'zi taxmin qilmaydi.
export default function KnowledgeCategoriesModal({ categories, t: admin, onClose, onChanged }: Props) {
  const ref = useModalA11y<HTMLDivElement>(onClose);
  const [name, setName] = useState("");
  const [kw, setKw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const add = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await createCategory({ name: name.trim(), keywords: splitKeywords(kw) });
      setName("");
      setKw("");
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={admin.knowledgeCategoriesTitle}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <div className={styles.title}>{admin.knowledgeCategoriesTitle}</div>
          <button type="button" className={styles.ghostBtn} onClick={onClose}>
            {admin.knowledgeCategoriesClose}
          </button>
        </div>
        <p className={styles.hint}>{admin.knowledgeCategoriesHint}</p>

        <div className={styles.list}>
          {categories.length === 0 ? (
            <div className={styles.empty}>{admin.knowledgeCategoryEmpty}</div>
          ) : (
            // Kalit + nom: saqlangandan keyin qator yangi qiymatlar bilan qayta chiziladi
            categories.map((c) => (
              <CategoryRow key={`${c.key}:${c.name}:${c.keywords.join(",")}`} cat={c} t={admin} onChanged={onChanged} />
            ))
          )}
        </div>

        <div className={`${styles.row} ${styles.newRow}`}>
          <div className={styles.fields}>
            <input
              className={styles.name}
              value={name}
              maxLength={100}
              onChange={(e) => setName(e.target.value)}
              placeholder={admin.knowledgeCategoryNamePh}
              aria-label={admin.knowledgeCategoryNamePh}
              disabled={busy}
            />
            <input
              className={styles.kw}
              value={kw}
              onChange={(e) => setKw(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void add();
              }}
              placeholder={admin.knowledgeCategoryKeywordsPh}
              aria-label={admin.knowledgeCategoryKeywordsPh}
              disabled={busy}
            />
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.saveBtn} onClick={() => void add()} disabled={busy || !name.trim()}>
              {admin.knowledgeCategoryAdd}
            </button>
          </div>
          {err && <div className={styles.err}>{err}</div>}
        </div>
      </div>
    </div>
  );
}
