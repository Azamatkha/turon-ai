import styles from "./OrbitRings.module.css";

/**
 * Logotip atrofidagi nozik orbita chiziqlari va ular bo'ylab sekin
 * aylanadigan sharchalar. Sof dekorativ fon elementi.
 *
 * Nega SVG + CSS: aylanish `transform: rotate` bilan bajariladi — ya'ni
 * kompozitor qatlamida, JS ham, har kadrda qayta chizish ham yo'q.
 * `prefers-reduced-motion` da animatsiya CSS darajasida o'chadi.
 *
 * Har bir sharcha IKKI guruhga o'ralgan:
 *   tashqi guruh — boshlang'ich burchak (`phase`, qo'zg'almas),
 *   ichki guruh — aylanish animatsiyasi.
 * Bitta guruhda ikkalasini berib bo'lmaydi: animatsiyadagi `rotate()`
 * statik `rotate()` ni butunlay almashtirib yuboradi.
 */

/** [radius, boshlang'ich burchak (°), sharcha radiusi, aylanish davri (s)] */
const DOTS: [number, number, number, number][] = [
  [150, 0, 4.5, 44],
  [150, 130, 3, 44],
  [150, 245, 3.5, 44],
  [230, 40, 5, 62],
  [230, 155, 3.5, 62],
  [230, 250, 4, 62],
  [230, 320, 3, 62],
  [310, 15, 4.5, 84],
  [310, 95, 3, 84],
  [310, 180, 5, 84],
  [310, 235, 3.5, 84],
  [310, 300, 4, 84],
];

const C = 360; // viewBox markazi

export default function OrbitRings({ className }: { className?: string }) {
  return (
    <svg
      className={`${styles.root} ${className ?? ""}`}
      viewBox="0 0 720 720"
      aria-hidden="true"
    >
      <circle className={styles.ring} cx={C} cy={C} r="150" />
      <circle className={styles.ring} cx={C} cy={C} r="230" />
      <circle className={styles.ring} cx={C} cy={C} r="310" />

      {DOTS.map(([radius, phase, size, duration], i) => (
        <g key={i} transform={`rotate(${phase} ${C} ${C})`}>
          <g
            className={styles.spin}
            style={{
              animationDuration: `${duration}s`,
              // Qo'shni halqalar qarama-qarshi yo'nalishda aylansin
              animationDirection: i % 2 ? "reverse" : "normal",
            }}
          >
            <circle
              className={styles.dot}
              cx={C}
              cy={C - radius}
              r={size}
            />
          </g>
        </g>
      ))}
    </svg>
  );
}
