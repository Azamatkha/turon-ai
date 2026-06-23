import { useEffect, useState } from "react";
import type { LoginStrings } from "../../types/i18n";
import styles from "./ProductPreviewCard.module.css";

const TARGET = 94;

// "Speedometr" effekti: foiz 0 dan TARGET gacha ko'tariladi va har necha
// sekundda qaytadan ishga tushadi (ringni ham to'ldiradi).
function useCountUp(target: number, duration = 1600, cycle = 4800) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let raf = 0;
    let startTs = 0;
    const animate = () => {
      startTs = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - startTs) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3); // ease-out
        setValue(Math.round(eased * target));
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    };
    animate();
    const interval = setInterval(() => {
      setValue(0);
      animate();
    }, cycle);
    return () => {
      cancelAnimationFrame(raf);
      clearInterval(interval);
    };
  }, [target, duration, cycle]);
  return value;
}

// Suzuvchi mahsulot oldindan ko'rinishi (chat karta + statistika kartasi)
export default function ProductPreviewCard({ t }: { t: LoginStrings }) {
  const pct = useCountUp(TARGET);

  return (
    <div className={styles.wrap}>
      <div className={styles.stack}>
        {/* asosiy chat karta */}
        <div className={styles.chatCard}>
          <div className={styles.chatCardHead}>
            <div className={styles.chatCardIcon}>
              <svg viewBox="0 0 300 304" width="14" height="14"><path d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z" fill="#dbe7f0" /></svg>
            </div>
            <div className={styles.chatCardMeta}>
              <div className={styles.chatCardName}>Turon AI</div>
              <div className={styles.chatCardStatus}>
                <span className={styles.statusDot} />
                {t.online}
              </div>
            </div>
            <div className={styles.chatCardVersion}>v2.5</div>
          </div>
          <div className={styles.bubbleRow}>
            <div className={`${styles.bubbleUser} ${styles.bubbleAnimUser}`}>{t.pvUser}</div>
          </div>
          <div className={styles.bubbleRowAi}>
            <div className={`${styles.bubbleAi} ${styles.bubbleAnimAi}`}>{t.pvAI}</div>
          </div>
        </div>

        {/* suzuvchi statistika karta */}
        <div className={styles.statCard}>
          <div className={styles.statLabel}>{t.statLabel}</div>
          <div className={styles.statRow}>
            <div
              className={styles.ring}
              style={{ background: `conic-gradient(#2a6f97 ${pct}%, #e3e8e2 ${pct}% 100%)` }}
            >
              <div className={styles.ringInner}>{pct}%</div>
            </div>
            <div className={styles.bars}>
              <div className={`${styles.barLow} ${styles.barAnim}`} />
              <div className={`${styles.barAccent} ${styles.barAnim}`} />
              <div className={`${styles.barMid} ${styles.barAnim}`} />
              <div className={`${styles.barStrong} ${styles.barAnim}`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
