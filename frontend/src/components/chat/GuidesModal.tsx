import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { MdOndemandVideo } from "react-icons/md";
import { guideVideoSrc, listGuides, type EdoGuide } from "../../services/guideService";
import { useModalA11y } from "../../hooks/useModalA11y";
import { ACCENT, PRIMARY_ON_DARK } from "./theme";
import type { ThemeTokens } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./GuidesModal.module.css";

interface GuidesModalProps {
  tk: ThemeTokens;
  isDark: boolean;
  s: ChatStaticStrings;
  onClose: () => void;
}

// EDO yo'riqnomalari: chapda ro'yxat, o'ngda video pleyer.
// Tor ekranda — avval ro'yxat, tanlanganda pleyer ("orqaga" bilan).
// Yo'riqnoma hali bo'lmasa (yoki yuklab bo'lmasa) — ikki ustun o'rniga
// bitta ixcham holat oynasi.
// Video bizning serverdan beriladi (YouTube emas — ko'p xodimda unga kirish yo'q).
export default function GuidesModal({ tk, isDark, s, onClose }: GuidesModalProps) {
  const [items, setItems] = useState<EdoGuide[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<EdoGuide | null>(null);

  const accent = isDark ? PRIMARY_ON_DARK : ACCENT;

  // Esc: video ochiq bo'lsa (tor ekranda) — ro'yxatga qaytadi, aks holda yopadi
  const modalRef = useModalA11y<HTMLDivElement>(() => {
    if (selected && window.matchMedia("(max-width: 760px)").matches) setSelected(null);
    else onClose();
  });

  useEffect(() => {
    // Video havolalari qisqa muddatli — har ochilishda ro'yxat yangidan olinadi
    listGuides()
      .then(setItems)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, []);

  // Ro'yxat yuklandi, lekin ko'rsatadigan narsa yo'q — bitta xabar yetarli
  const emptyState = !loading && (failed || items.length === 0);

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div
        ref={modalRef}
        className={`${styles.modal} ${selected ? styles.hasSelection : ""} ${emptyState ? styles.modalEmpty : ""}`}
        style={{ background: tk.card, border: `1px solid ${tk.cardBorder}` }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={s.guidesTitle}
      >
        <div className={styles.head}>
          <div className={styles.headTitle} style={{ color: tk.strong }}>
            <MdOndemandVideo size={21} color={accent} />
            {s.guidesTitle}
          </div>
          <button className={styles.closeBtn} style={{ color: tk.muted }} onClick={onClose} aria-label={s.close}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </button>
        </div>

        {emptyState ? (
          <div className={styles.emptyState} style={{ color: failed ? "#DC2626" : tk.muted }}>
            <MdOndemandVideo size={44} color={accent} aria-hidden="true" />
            <span>{failed ? s.guidesError : s.guidesEmpty}</span>
          </div>
        ) : (
        <div className={styles.body}>
          <div className={styles.listPane}>
            <div className={styles.list} aria-busy={loading}>
              {loading ? (
                <div className={styles.state} style={{ color: tk.muted }}>{s.dirLoading}</div>
              ) : (
                items.map((g) => {
                  const active = selected?.id === g.id;
                  return (
                    <button
                      key={g.id}
                      type="button"
                      className={styles.row}
                      aria-current={active ? "true" : undefined}
                      onClick={() => setSelected(g)}
                      style={{
                        color: tk.strong,
                        background: active ? "rgba(90, 120, 224, 0.16)" : undefined,
                      }}
                    >
                      <span className={styles.rowIcon} aria-hidden="true">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
                      </span>
                      <span className={styles.rowTitle}>{g.title}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className={styles.playerPane}>
            {selected ? (
              <>
                <button type="button" className={styles.backBtn} style={{ color: accent }} onClick={() => setSelected(null)}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
                  {s.dirBack}
                </button>
                <div className={styles.videoTitle} style={{ color: tk.strong }}>{selected.title}</div>
                {/* key — boshqa video tanlanganda pleyer noldan boshlansin */}
                <video
                  key={selected.id}
                  className={styles.video}
                  src={guideVideoSrc(selected)}
                  controls
                  autoPlay
                  preload="metadata"
                  playsInline
                  controlsList="nodownload"
                />
              </>
            ) : (
              <div className={styles.placeholder} style={{ color: tk.muted, borderColor: tk.cardBorder }}>
                <MdOndemandVideo size={40} color={accent} aria-hidden="true" />
                <span>{s.guidesPick}</span>
              </div>
            )}
          </div>
        </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
