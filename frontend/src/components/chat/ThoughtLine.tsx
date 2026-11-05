import { useState } from "react";
import type { ThinkStep } from "../../types/chat";
import type { ChatStaticStrings } from "../../types/i18n";
import styles from "./ThoughtLine.module.css";

// Bot javobi oldidagi "O'ylayapman… 2.2s" qatori.
//  * working=true  — yulduzcha "nafas oladi", matn yaltiraydi, soat yuradi,
//    bosqichlar ochiq (oxirgisi — hozirgi, pulsatsiya qiladi);
//  * working=false — "3.4 soniya o'yladi ⌄" bo'lib yig'iladi, bosilsa
//    o'tgan bosqichlar ochiladi.
// Bosqichlar backend'dan keladi (qara: execute_stream status hodisalari) —
// taymer bilan soxta qadam ko'rsatilmaydi.
interface ThoughtLineProps {
  working: boolean;
  seconds: number;
  steps: ThinkStep[];
  s: ChatStaticStrings;
  color: string;
  accent: string;
}

const fmt = (sec: number) => Math.max(0, sec).toFixed(1);

export default function ThoughtLine({ working, seconds, steps, s, color, accent }: ThoughtLineProps) {
  // Ishlayotganda ochiq; tayyor javob ustida esa yig'iq turadi
  const [open, setOpen] = useState(working);
  const hasSteps = steps.length > 0;
  const expanded = hasSteps && (working || open);

  return (
    <div className={`${styles.root} ${working ? styles.working : ""}`} style={{ color }}>
      <button
        type="button"
        className={styles.head}
        onClick={() => !working && hasSteps && setOpen((v) => !v)}
        aria-expanded={hasSteps ? expanded : undefined}
        disabled={working || !hasSteps}
      >
        <span className={styles.glyph} style={{ color: accent }} aria-hidden="true">
          <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round">
            <path d="M12 3c.5 4.2 2.8 6.5 7 7-4.2.5-6.5 2.8-7 7-.5-4.2-2.8-6.5-7-7 4.2-.5 6.5-2.8 7-7Z" />
            <path d="M19 15.5c.2 1.6 1 2.4 2.5 2.5-1.5.2-2.3 1-2.5 2.5-.2-1.5-1-2.3-2.5-2.5 1.5-.1 2.3-.9 2.5-2.5Z" />
          </svg>
        </span>
        <span className={working ? styles.shimmer : styles.label}>
          {working ? s.thinkingLabel : s.thoughtFor(fmt(seconds))}
        </span>
        {working && <span className={styles.timer}>{fmt(seconds)}s</span>}
        {hasSteps && (
          <svg className={`${styles.chevron} ${expanded ? styles.chevronOpen : ""}`} viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        )}
        {/* Ekran o'quvchisi uchun — bosqich o'zgarganda o'qiladi */}
        <span className={styles.sr} role="status">
          {working ? s.thinkSteps[steps[steps.length - 1]] ?? s.thinkingLabel : s.thoughtFor(fmt(seconds))}
        </span>
      </button>

      {hasSteps && (
        <div className={`${styles.trace} ${expanded ? styles.traceOpen : ""}`} aria-hidden={!expanded}>
          <div className={styles.fold}>
            {steps.map((st, i) => {
              const done = !working || i < steps.length - 1;
              return (
                <div key={st + i} className={`${styles.step} ${done ? styles.stepDone : ""}`}>
                  <span className={styles.mark} style={done ? undefined : { color: accent }} aria-hidden="true">
                    {done ? (
                      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <i className={styles.pulse} />
                    )}
                  </span>
                  <span>{s.thinkSteps[st]}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
