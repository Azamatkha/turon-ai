import { useState } from "react";
import type { ChatStaticStrings } from "../../types/i18n";
import type { ThemeTokens, VoteReason } from "../../types/chat";
import styles from "./DislikeFeedback.module.css";

interface DislikeFeedbackProps {
  s: ChatStaticStrings;
  tk: ThemeTokens;
  accent: string;
  onSubmit: (reason: VoteReason, comment: string) => void;
  onClose: () => void;
}

// Dislike bosilgandan keyin javob tagida ochiladigan kichik panel: sabab
// tanlanadi (+ ixtiyoriy izoh) va adminning "Yoqmagan javoblar" ro'yxatiga
// tushadi. Yopib ketsa ham dislike o'zi saqlangan bo'ladi.
export default function DislikeFeedback({ s, tk, accent, onSubmit, onClose }: DislikeFeedbackProps) {
  const [reason, setReason] = useState<VoteReason | null>(null);
  const [comment, setComment] = useState("");

  const reasons: { id: VoteReason; label: string }[] = [
    { id: "wrong", label: s.dislikeReasonWrong },
    { id: "outdated", label: s.dislikeReasonOutdated },
    { id: "incomplete", label: s.dislikeReasonIncomplete },
    { id: "other", label: s.dislikeReasonOther },
  ];

  return (
    <div
      className={styles.panel}
      style={{ background: tk.card, border: "1px solid " + tk.cardBorder, color: tk.strong }}
      role="group"
      aria-label={s.dislikeTitle}
    >
      <div className={styles.head}>
        <span className={styles.title}>{s.dislikeTitle}</span>
        <button type="button" className={styles.close} onClick={onClose} aria-label={s.dislikeClose} style={{ color: tk.muted }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </div>
      <div className={styles.reasons}>
        {reasons.map((r) => {
          const on = reason === r.id;
          return (
            <button
              key={r.id}
              type="button"
              className={styles.reason}
              aria-pressed={on}
              onClick={() => setReason(on ? null : r.id)}
              style={{
                border: "1px solid " + (on ? accent : tk.cardBorder),
                background: on ? accent : "transparent",
                color: on ? "#fff" : tk.strong,
              }}
            >
              {r.label}
            </button>
          );
        })}
      </div>
      <textarea
        className={styles.comment}
        value={comment}
        maxLength={500}
        rows={2}
        placeholder={s.dislikeCommentPh}
        onChange={(e) => setComment(e.target.value)}
        style={{ border: "1px solid " + tk.cardBorder, color: tk.strong, background: tk.bg }}
      />
      <div className={styles.foot}>
        <button
          type="button"
          className={styles.send}
          disabled={!reason}
          onClick={() => reason && onSubmit(reason, comment.trim())}
          style={{ background: accent }}
        >
          {s.dislikeSend}
        </button>
      </div>
    </div>
  );
}
