import type { LoginStrings } from "../../types/i18n";
import styles from "./ProductPreviewCard.module.css";

// Suzuvchi mahsulot oldindan ko'rinishi (chat karta + statistika kartasi)
export default function ProductPreviewCard({ t }: { t: LoginStrings }) {
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
            <div className={styles.bubbleUser}>{t.pvUser}</div>
          </div>
          <div className={styles.bubbleRowAi}>
            <div className={styles.bubbleAi}>{t.pvAI}</div>
          </div>
        </div>

        {/* suzuvchi statistika karta */}
        <div className={styles.statCard}>
          <div className={styles.statLabel}>{t.statLabel}</div>
          <div className={styles.statRow}>
            <div className={styles.ring}>
              <div className={styles.ringInner}>94%</div>
            </div>
            <div className={styles.bars}>
              <div className={styles.barLow} />
              <div className={styles.barAccent} />
              <div className={styles.barMid} />
              <div className={styles.barStrong} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
