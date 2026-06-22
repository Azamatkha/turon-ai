import type { ThemeTokens } from "../../types/chat";
import styles from "./ThemeToggle.module.css";

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
  tk: ThemeTokens;
}

// Mavzu (light/dark) almashtirgich
export default function ThemeToggle({ isDark, onToggle, tk }: ThemeToggleProps) {
  return (
    <div className={styles.wrap}>
      <span className={styles.label} style={{ color: isDark ? tk.muted : tk.strong }}>Light</span>
      <button onClick={onToggle} title="Mavzu" className={`${styles.switch} ${isDark ? styles.switchDark : styles.switchLight}`}>
        <span className={`${styles.knob} ${isDark ? styles.knobDark : styles.knobLight}`}>
          {isDark ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#173f73"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" /></svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f5a623" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="4.5" fill="#f5a623" stroke="none" />
              <line x1="12" y1="2.5" x2="12" y2="5" />
              <line x1="12" y1="19" x2="12" y2="21.5" />
              <line x1="2.5" y1="12" x2="5" y2="12" />
              <line x1="19" y1="12" x2="21.5" y2="12" />
              <line x1="4.9" y1="4.9" x2="6.6" y2="6.6" />
              <line x1="17.4" y1="17.4" x2="19.1" y2="19.1" />
              <line x1="4.9" y1="19.1" x2="6.6" y2="17.4" />
              <line x1="17.4" y1="6.6" x2="19.1" y2="4.9" />
            </svg>
          )}
        </span>
        <span className={`${styles.starSm} ${isDark ? styles.starVisible : styles.starHidden}`} />
        <span className={`${styles.starXs} ${isDark ? styles.starXsVisible : styles.starHidden}`} />
      </button>
      <span className={styles.label} style={{ color: isDark ? tk.strong : tk.muted }}>Dark</span>
    </div>
  );
}
