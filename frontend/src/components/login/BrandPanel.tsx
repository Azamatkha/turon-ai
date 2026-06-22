import DotField from "../DotField";
import Logo from "../common/Logo";
import ProductPreviewCard from "./ProductPreviewCard";
import type { LoginStrings } from "../../types/i18n";
import styles from "./BrandPanel.module.css";

// Chap, qoraygan brend paneli — logo, suzuvchi mahsulot ko'rinishi va sarlavha bloki
export default function BrandPanel({ t }: { t: LoginStrings }) {
  return (
    <div className={styles.panel}>
      <div className={styles.blobTop} />
      <div className={styles.blobBottom} />
      {/* interaktiv nuqta-to'r foni (sichqoncha yaqinida nuqtalar "bo'rtadi") */}
      <div className={styles.dotMask}>
        <DotField
          dotRadius={5}
          dotSpacing={18}
          bulgeOnly
          bulgeStrength={32}
          cursorRadius={220}
          glowRadius={170}
          gradientFrom="#2c5570"
          gradientTo="#3f7197"
          glowColor="rgba(191,224,240,0.14)"
        />
      </div>
      {/* sochilgan bezak kvadratchalar */}
      <div className={styles.deco1} />
      <div className={styles.deco2} />
      <div className={styles.deco3} />

      {/* logo */}
      <div className={styles.logoRow}>
        <div className={styles.logoIcon}>
          <Logo size={32} />
        </div>
        <div className={styles.logoText}>
          Turon<span className={styles.logoTextAi}> AI</span>
        </div>
      </div>

      <ProductPreviewCard t={t} />

      {/* sarlavha bloki */}
      <div className={styles.headlineBlock}>
        <div className={styles.badge}>
          <span className={styles.badgeDot} />
          {t.badge}
        </div>
        <h1 className={styles.headline}>{t.headline}</h1>
        <p className={styles.subtext}>{t.sub}</p>
        {/* pastki SSO qatori */}
        <div className={styles.ssoRow}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
          </svg>
          {t.sso}
        </div>
      </div>
    </div>
  );
}
