import DotField from "../DotField";
import styles from "./PageBackground.module.css";

// Sahifa foni: aurora dog'lari + interaktiv nuqta-to'r (login qutisidan tashqarida).
// DotField pageX koordinatalaridan foydalangani uchun masshtab 100% dan past
// bo'lganda ham (90%, 80%) nuqtalar "sizib chiqmaydi".
export default function PageBackground() {
  return (
    <>
      <div className={styles.auroraLayer}>
        <div className={styles.blobTopLeft} />
        <div className={styles.blobBottomRight} />
        <div className={styles.blobMiddle} />
      </div>
      <div className={styles.dotLayer}>
        <DotField
          dotRadius={4}
          dotSpacing={22}
          bulgeOnly
          bulgeStrength={26}
          cursorRadius={240}
          glowRadius={180}
          gradientFrom="#c2cdd2"
          gradientTo="#aebfc7"
          glowColor="rgba(42,111,151,0.10)"
        />
      </div>
    </>
  );
}
