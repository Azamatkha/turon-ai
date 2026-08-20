import type { AdminStrings } from "../../types/i18n";
import styles from "./ActivityMix.module.css";

export interface MixSegment {
  label: string;
  value: number;
  color: string;
}

interface ActivityMixProps {
  segments: MixSegment[];
  mounted: boolean;
  t: AdminStrings;
}

/**
 * So'nggi faollik tarkibi — bitta gorizontal ustunda to'plangan (stacked)
 * diagramma.
 *
 * NEGA HALQA EMAS: bo'lakchalar soni 4 ta va ular "kirish / chiqish /
 * suhbat / xabar" kabi bir-biriga yaqin miqdorlar. Halqada bunday yaqin
 * ulushlarni burchak bo'yicha solishtirish qiyin, gorizontal uzunlikni esa
 * ko'z aniq o'lchaydi. Ustiga bu karta pastda, keng va past joyga tushadi —
 * gorizontal shakl o'sha joyga to'g'ri keladi.
 *
 * DIQQAT: bu ma'lumot butun tarixni emas, backend qaytargan SO'NGGI
 * hodisalar ro'yxatini yoritadi. Sarlavha osti shuni ochiq aytadi, aks holda
 * grafik "umumiy statistika" bo'lib o'qilardi.
 */
export default function ActivityMix({ segments, mounted, t: admin }: ActivityMixProps) {
  const shown = segments.filter((s) => s.value > 0);
  const total = shown.reduce((s, x) => s + x.value, 0);

  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.activityMixTitle}</div>
      <div className={styles.sub}>{admin.activityMixSub}</div>

      {total === 0 ? (
        <div className={styles.empty}>{admin.chartNoData}</div>
      ) : (
        <>
          <div className={styles.track} role="img" aria-label={admin.activityMixTitle}>
            {shown.map((s, i) => (
              <div
                key={s.label}
                className={styles.seg}
                // HTML segment — SVG emas, shuning uchun tooltip `<title>`
                // elementi bilan emas, `title` atributi bilan beriladi.
                title={`${s.label}: ${s.value.toLocaleString()}`}
                style={{
                  background: s.color,
                  // Kengligi 0 dan o'sadi. `flex-basis` emas, `width` —
                  // segmentlar orasidagi 2px tirqish flex `gap` bilan
                  // beriladi va u kenglik hisobiga aralashmaydi.
                  width: mounted ? `${(s.value / total) * 100}%` : "0%",
                  transitionDelay: `${i * 0.06}s`,
                }}
              />
            ))}
          </div>

          {/* Rang yolg'iz belgilovchi bo'lmasligi uchun har segment nomi va
              soni matn bilan takrorlanadi. */}
          <ul className={styles.legend}>
            {shown.map((s) => (
              <li key={s.label} className={styles.legendRow}>
                <span className={styles.dot} style={{ background: s.color }} aria-hidden />
                <span className={styles.legendName}>{s.label}</span>
                <span className={styles.legendValue}>{s.value.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
