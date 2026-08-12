import styles from "./OrbitRings.module.css";

/**
 * Logotip atrofidagi uchta nozik orbita chizig'i va ular bo'ylab sekin
 * aylanadigan sharchalar. Sof dekorativ fon elementi — hech qanday
 * o'lchov yoki holatni bildirmaydi.
 *
 * Nega SVG + CSS: aylanish `transform: rotate` bilan bajariladi, ya'ni
 * kompozitor qatlamida — JS ham, har kadrda qayta chizish ham yo'q.
 * `prefers-reduced-motion` da animatsiya CSS darajasida o'chadi.
 */
export default function OrbitRings({ className }: { className?: string }) {
  return (
    <svg
      className={`${styles.root} ${className ?? ""}`}
      viewBox="0 0 720 720"
      aria-hidden="true"
    >
      <circle className={styles.ring} cx="360" cy="360" r="150" />
      <circle className={styles.ring} cx="360" cy="360" r="230" />
      <circle className={styles.ring} cx="360" cy="360" r="310" />

      {/* Har bir sharcha o'z guruhida aylanadi — tezliklar turlicha */}
      <g className={`${styles.spin} ${styles.spin1}`}>
        <circle className={styles.dot} cx="360" cy="210" r="5" />
      </g>
      <g className={`${styles.spin} ${styles.spin2}`}>
        <circle className={styles.dot} cx="360" cy="130" r="4" />
      </g>
      <g className={`${styles.spin} ${styles.spin3}`}>
        <circle className={styles.dot} cx="360" cy="670" r="4.5" />
      </g>
      <g className={`${styles.spin} ${styles.spin4}`}>
        <circle className={styles.dot} cx="360" cy="590" r="3.5" />
      </g>
    </svg>
  );
}
