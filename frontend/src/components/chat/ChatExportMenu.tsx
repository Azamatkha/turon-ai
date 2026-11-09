import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MdOutlineFileDownload } from "react-icons/md";
import { downloadSessionDocx } from "../../services/chatHistoryService";
import { saveBlob } from "../../utils/saveBlob";
import type { Lang } from "../../types/lang";
import type { Msg, ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import MessageContent from "./MessageContent";
import styles from "./ChatExportMenu.module.css";

interface Props {
  sessionId: string;
  title: string;
  messages: Msg[];
  lang: Lang;
  tk: ThemeTokens;
  s: ChatStaticStrings;
}

function fmt(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Suhbatni yuklab olish: Word (.docx — backend yasaydi) yoki PDF (brauzerning
// chop etish oynasi -> "PDF sifatida saqlash"). PDF uchun alohida chop etish
// ko'rinishi portal orqali <body>ga chiqariladi; qolgan sahifa chop etishda
// yashiriladi (index.css -> .tu-print-root).
export default function ChatExportMenu({ sessionId, title, messages, lang, tk, s }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(false);
  const [printing, setPrinting] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Chop etish ko'rinishi DOM'ga tushgach print oynasini ochamiz, yopilgach olib tashlaymiz
  useEffect(() => {
    if (!printing) return;
    const done = () => setPrinting(false);
    window.addEventListener("afterprint", done);
    const id = window.setTimeout(() => window.print(), 50);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("afterprint", done);
    };
  }, [printing]);

  const docx = async () => {
    setBusy(true);
    setErr(false);
    try {
      const { blob, filename } = await downloadSessionDocx(sessionId, lang);
      saveBlob(blob, filename);
      setOpen(false);
    } catch {
      setErr(true);
    } finally {
      setBusy(false);
    }
  };

  const pdf = () => {
    setOpen(false);
    setPrinting(true);
  };

  const shown = messages.filter((m) => m.text.trim());

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        style={{ color: tk.muted }}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={s.exportChat}
        data-tip={s.exportChat}
      >
        <MdOutlineFileDownload size={17} />
      </button>
      {open && (
        <div className={styles.menu} role="menu" style={{ background: tk.card, border: "1px solid " + tk.cardBorder, color: tk.strong }}>
          <button type="button" role="menuitem" className={styles.item} onClick={() => void docx()} disabled={busy}>
            <span className={`${styles.badge} ${styles.word}`}>W</span>
            {busy ? "…" : s.exportDocx}
          </button>
          <button type="button" role="menuitem" className={styles.item} onClick={pdf}>
            <span className={`${styles.badge} ${styles.pdf}`}>PDF</span>
            {s.exportPdf}
          </button>
          {err && <div className={styles.err}>{s.exportError}</div>}
        </div>
      )}

      {printing &&
        createPortal(
          <div className={`tu-print-root ${styles.print}`}>
            <h1 className={styles.printTitle}>{title}</h1>
            <div className={styles.printMeta}>Turon AI · {fmt(new Date().toISOString())}</div>
            {shown.map((m) => (
              <section key={m.id} className={styles.printMsg}>
                <div className={styles.printWho}>
                  {m.role === "user" ? s.exportYou : "Turon AI"}
                  {m.time && <span className={styles.printTime}> · {fmt(m.time)}</span>}
                </div>
                <div className={styles.printBody}>
                  <MessageContent text={m.text} />
                </div>
              </section>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
}
