import { useState } from "react";
import { setKnowledgeValidity } from "../../services/knowledgeService";
import type { AdminStrings } from "../../types/i18n";
import { fmtIsoDate, todayIso, validityState } from "../../utils/knowledgeValidity";
import styles from "./KnowledgeValidityEditor.module.css";

interface Props {
  title: string;
  // Hozirgi muddat "YYYY-MM-DD" yoki "" (muddatsiz)
  validUntil: string;
  t: AdminStrings;
  onSaved: () => void;
}

// Hujjat sahifasidagi "Amal qilish muddati": sana tanlash, saqlash yoki
// muddatsiz qilish. Holat belgisi ro'yxatdagi bilan bir xil ranglarda.
export default function KnowledgeValidityEditor({ title, validUntil, t: admin, onSaved }: Props) {
  const [value, setValue] = useState(validUntil);
  const [saved, setSaved] = useState(validUntil);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const save = async (next: string | null) => {
    setBusy(true);
    setErr(null);
    setOk(false);
    try {
      await setKnowledgeValidity(title, next);
      setSaved(next ?? "");
      setValue(next ?? "");
      setOk(true);
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.knowledgeSaveError);
    } finally {
      setBusy(false);
    }
  };

  const st = validityState(saved);
  const stateCls = st === "expired" ? styles.expired : st === "soon" ? styles.soon : styles.okState;

  return (
    <div className={styles.box}>
      <div className={styles.head}>
        <span className={styles.label}>{admin.knowledgeValidityLabel}</span>
        <span className={`${styles.state} ${saved ? stateCls : styles.none}`}>
          {saved
            ? `${st === "expired" ? admin.knowledgeValidityExpired : admin.knowledgeValidityUntil} ${fmtIsoDate(saved)}`
            : admin.knowledgeValidityNone}
        </span>
      </div>
      <div className={styles.row}>
        <input
          type="date"
          className={styles.date}
          value={value}
          min={saved && saved < todayIso() ? undefined : todayIso()}
          onChange={(e) => {
            setValue(e.target.value);
            setOk(false);
          }}
          aria-label={admin.knowledgeValidityLabel}
        />
        <button
          type="button"
          className={styles.saveBtn}
          onClick={() => void save(value || null)}
          disabled={busy || value === saved}
        >
          {admin.knowledgeValiditySave}
        </button>
        {saved && (
          <button type="button" className={styles.clearBtn} onClick={() => void save(null)} disabled={busy}>
            {admin.knowledgeValidityClear}
          </button>
        )}
        {ok && <span className={styles.ok} role="status">{admin.knowledgeValiditySaved}</span>}
      </div>
      {err && <div className={styles.err}>{err}</div>}
      <p className={styles.hint}>{admin.knowledgeValidityHint}</p>
    </div>
  );
}
