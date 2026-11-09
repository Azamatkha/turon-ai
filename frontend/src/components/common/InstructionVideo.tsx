import { useRef, useState } from "react";
import styles from "./InstructionVideo.module.css";

interface Props {
  src: string;
  // Video ustidagi "ko'ring" degan jonli yozuv
  nudge: string;
  // Boshlashdan oldingi tugma yozuvi
  playLabel: string;
  // Video tugagandan keyingi "qayta ko'rish" tugmasi
  replayLabel: string;
  // Video tugagach chiqadigan qisqa matn
  endedText: string;
}

type Phase = "idle" | "playing" | "ended";

// Verifikatsiya bo'yicha qo'llanma video: boshida katta "play" tugmasi
// (pulsatsiya bilan), tugaganda — "qayta ko'rish" qatlami.
export default function InstructionVideo({ src, nudge, playLabel, replayLabel, endedText }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  const [phase, setPhase] = useState<Phase>("idle");

  const play = () => {
    const v = ref.current;
    if (!v) return;
    if (phase === "ended") v.currentTime = 0;
    void v.play();
  };

  return (
    <div className={styles.wrap}>
      {/* Videoni ko'rishga undovchi jonli yozuv — faqat hali ko'rilmaganda */}
      <div className={`${styles.nudge} ${phase === "playing" ? styles.nudgeHidden : ""}`}>
        <span className={styles.nudgeText}>{nudge}</span>
        <span className={styles.nudgeArrow} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12l7 7 7-7" /></svg>
        </span>
      </div>

      <div className={styles.frame}>
        <video
          ref={ref}
          className={styles.video}
          src={src}
          preload="metadata"
          playsInline
          controls={phase === "playing"}
          onPlay={() => setPhase("playing")}
          onEnded={() => setPhase("ended")}
        />

        {phase !== "playing" && (
          <button type="button" className={styles.overlay} onClick={play} aria-label={phase === "ended" ? replayLabel : playLabel}>
            {phase === "ended" && <span className={styles.endedText}>{endedText}</span>}
            <span className={`${styles.playBtn} ${phase === "idle" ? styles.pulse : ""}`} aria-hidden="true">
              {phase === "ended" ? (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></svg>
              ) : (
                <svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5Z" /></svg>
              )}
            </span>
            <span className={styles.playLabel}>{phase === "ended" ? replayLabel : playLabel}</span>
          </button>
        )}
      </div>
    </div>
  );
}
