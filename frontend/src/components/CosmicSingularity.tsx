import { useEffect, useRef } from "react";

/**
 * Fon zarrachalari buluti.
 *
 * Uch xil holat:
 *   1. BO'SH — zarrachalar o'z "uy" nuqtasi atrofida juda sekin suzadi;
 *   2. KURSOR HARAKATDA — yaqindagilar unga tortiladi (to'planadi);
 *   3. KURSOR JOYIDA TURSA (`holdDelay` dan uzoq) — zarrachalar aylanib
 *      kelib LOGOTIP shaklini hosil qiladi, kursor qimirlashi bilan
 *      tarqalib, uylariga qaytadi.
 *
 * Logotip shakli qanday olinadi: `Logo` komponentidagi SVG path aynan shu
 * yerda `Path2D` bilan ko'rinmas (offscreen) canvas'ga chiziladi, so'ng
 * `getImageData` orqali to'ldirilgan piksellar "nishon nuqtalar" ro'yxatiga
 * yig'iladi. Ya'ni rasm yuklash ham, qo'lda yozilgan koordinatalar ham
 * kerak emas — logotip o'zgarsa, faqat quyidagi `LOGO_PATH` yangilanadi.
 *
 * Namuna sifatida `lightswind/cosmic-singularity-background` olingan, lekin
 * u three.js/WebGL da 25 000 zarracha chizadi. Bu loyihada fon aynan GPU
 * yuki sababli olib tashlangan (bank kompyuterlari kuchsiz), shuning uchun
 * bu yerda 2D canvas'dagi yengil variant.
 */

/** Logotip konturi — `components/common/Logo.tsx` bilan bir xil. */
const LOGO_PATH =
  "M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z";
const LOGO_VB = { w: 300, h: 304 };

interface CosmicSingularityProps {
  particleCount?: number;
  /** Bo'sh holatdagi suzish tezligi ko'paytiruvchisi. */
  speed?: number;
  /** Sichqonchaga tortilish kuchi. 0 — o'chirilgan. */
  attraction?: number;
  /** Sichqoncha ta'sir doirasi (piksel). */
  pointerRadius?: number;
  /** Kursor shuncha ms qimirlamasa — logotip yig'iladi. 0 — o'chirilgan. */
  holdDelay?: number;
  /** Yig'iladigan logotip o'lchami (piksel). */
  logoSize?: number;
  /** Zarracha ranglari (hex). Berilmasa — mavzuga mos to'plam. */
  colors?: string[];
  opacity?: number;
  isDark?: boolean;
  className?: string;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  /** "Uy" nuqtasi — zarracha bo'sh holatda shu joyga qaytadi. */
  hx: number;
  hy: number;
  /** Uy nuqtasining o'z sekin siljishi (px/ms). */
  hvx: number;
  hvy: number;
  size: number;
  /** Logotipdagi nishon nuqta indeksi. -1 — bu zarracha shaklga
      qo'shilmaydi, fon bo'm-bo'sh qolmasligi uchun joyida qoladi. */
  slot: number;
}

// Yorug' mavzuda ochiq havorang deyarli ko'rinmasdi — to'plam to'qlashtirildi
const LIGHT_COLORS = ["#003978", "#0B5FA5", "#1A7CC8", "#25507F", "#1F8F87", "#4A57C0"];
const DARK_COLORS = ["#63B3F0", "#9ED8FF", "#5FA3D6", "#8C93E8", "#4FD1C5", "#3B82C4"];

const withAlpha = (hex: string, alpha: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha.toFixed(3)})`;
};

/**
 * Logotipni ko'rinmas canvas'ga chizib, to'ldirilgan piksellardan nishon
 * nuqtalar ro'yxatini tuzadi (markazga nisbatan, ya'ni -w/2..w/2).
 */
function buildLogoTargets(size: number, want: number) {
  const off = document.createElement("canvas");
  off.width = size;
  off.height = size;
  const octx = off.getContext("2d", { willReadFrequently: true });
  if (!octx) return [] as { x: number; y: number }[];

  const k = size / Math.max(LOGO_VB.w, LOGO_VB.h);
  octx.translate((size - LOGO_VB.w * k) / 2, (size - LOGO_VB.h * k) / 2);
  octx.scale(k, k);
  octx.fillStyle = "#000";
  octx.fill(new Path2D(LOGO_PATH));

  const data = octx.getImageData(0, 0, size, size).data;
  const filled = (x: number, y: number) => data[(y * size + x) * 4 + 3] > 128;

  // Nechta piksel to'ldirilganini sanaymiz — kerakli QADAM shundan chiqadi.
  let count = 0;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) if (filled(x, y)) count++;
  }

  // MUHIM: nuqtalar TO'R (grid) bo'yicha olinadi. Ilgari barcha piksellar
  // qator-qator ro'yxatga yig'ilib, undan har N-chisi tanlanardi — qator
  // uzunligi bilan qadam "rezonansga" kirib, natijada logotip to'lmasdan
  // faqat diagonal chiziqlar chiqardi.
  const step = Math.max(1, Math.round(Math.sqrt(count / Math.max(1, want))));
  const points: { x: number; y: number }[] = [];
  for (let y = 0; y < size; y += step) {
    for (let x = 0; x < size; x += step) {
      if (filled(x, y)) points.push({ x: x - size / 2, y: y - size / 2 });
    }
  }
  return points;
}

export default function CosmicSingularity({
  // Kamroq, lekin yirikroq va to'qroq zarracha — 3200 tasi fonni
  // "chang bosgan" ko'rinishga solib qo'yardi.
  particleCount = 1500,
  speed = 1,
  attraction = 1,
  pointerRadius = 320,
  holdDelay = 650,
  // Kursordan sal kattaroq — 140 px hali ham yirik ko'rinardi.
  logoSize = 60,
  colors,
  opacity = 0.7,
  isDark = false,
  className,
}: CosmicSingularityProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const palette = (colors ?? (isDark ? DARK_COLORS : LIGHT_COLORS)).map((c) =>
      withAlpha(c, opacity),
    );
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let frame = 0;
    let last = 0;
    /** Canvas'ning ekrandagi o'rni — sichqoncha koordinatasini ko'chirish uchun. */
    let rect = { left: 0, top: 0 };
    let pointer: { x: number; y: number } | null = null;
    /** Kursor oxirgi marta sezilarli siljigan payt (ms). */
    let movedAt = 0;
    /** Logotip yig'ilyaptimi. */
    let forming = false;

    const particles: Particle[] = [];
    /** Rang bo'yicha guruhlangan indekslar — bir marta tuziladi. */
    const groups: number[][] = palette.map(() => []);
    // Zarrachalarning 65% i shaklga yig'iladi, 35% i fonda qoladi.
    // (30% da logotip to'lmasdi, 70% da esa fon bo'shab qolardi.)
    const formerCount = Math.round(particleCount * 0.65);
    const targets = holdDelay > 0 ? buildLogoTargets(logoSize, formerCount) : [];

    const setSize = () => {
      const parent = canvas.parentElement;
      const nw = parent?.clientWidth || window.innerWidth;
      const nh = parent?.clientHeight || window.innerHeight;
      const box = canvas.getBoundingClientRect();
      rect = { left: box.left, top: box.top };
      if (nw === w && nh === h) return;
      const first = w === 0;
      const sx = first ? 1 : nw / w;
      const sy = first ? 1 : nh / h;
      w = nw;
      h = nh;
      canvas.width = w;
      canvas.height = h;
      if (first) {
        let slot = 0;
        for (let i = 0; i < particleCount; i++) {
          const x = Math.random() * w;
          const y = Math.random() * h;
          // Uy nuqtasining siljishi: ~1..3 px/sek — deyarli sezilmaydi
          const ang = Math.random() * Math.PI * 2;
          const sp = (0.001 + Math.random() * 0.002) * speed;
          particles.push({
            x, y,
            vx: 0, vy: 0,
            hx: x, hy: y,
            hvx: Math.cos(ang) * sp,
            hvy: Math.sin(ang) * sp,
            // Kattaroq zarracha: 1–2 px "chang" bo'lib ko'rinmaydi
            size: Math.random() < 0.25 ? 3 : 2,
            // Har o'ntadan oltitasi-yettitasi shaklga qo'shiladi (butun
            // ekran bo'ylab bir tekis tarqalgan holda), qolgani fonda
            // qoladi. Har biriga O'ZINING nishoni tegadi — shuning uchun
            // nuqtalar ustma-ust tushmaydi.
            slot: i % 20 < 13 && slot < targets.length ? slot++ : -1,
          });
          groups[i % groups.length].push(i);
        }
      } else {
        // O'lcham o'zgarsa zarrachalar nisbatan joyida qolsin
        for (const p of particles) {
          p.x *= sx;
          p.y *= sy;
          p.hx *= sx;
          p.hy *= sy;
        }
      }
    };

    const step = (dt: number) => {
      /** Uyga qaytarish "prujinasi" — qaytish tezligi ~30 px/sek. */
      const spring = 0.0000022;
      /** Kursorga tortilish — qaytishdan ancha kuchli. */
      const pull = attraction * 0.0022;
      const r2 = pointerRadius * pointerRadius;
      const damp = Math.pow(0.9, dt / 16.67);
      const formable = forming && pointer && targets.length > 0;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        if (formable && pointer && p.slot >= 0) {
          // --- Logotip yig'ilishi -------------------------------------
          const t = targets[p.slot];
          const tx = pointer.x + t.x;
          const ty = pointer.y + t.y;
          const dx = tx - p.x;
          const dy = ty - p.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          // Radial tortilish + perpendikulyar (burama) tashkil etuvchi:
          // shundan zarracha to'g'ri uchmay, aylanib kelib joylashadi.
          // Nishonga yaqinlashgan sari burama so'nadi.
          // Koeffitsiyentlar ataylab kichik: ilgari zarrachalar bir zumda
          // "otilib" borardi, endi ~2 sekundda oqib kelib joylashadi.
          // Har kadrda qolgan masofaning ~3% i bosib o'tiladi: shakl ~2
          // sekundda to'liq yig'iladi. (0.000004 da "dumi" cho'zilib,
          // oxirgi zarrachalar 15 sekundgacha kelardi.)
          const swirl = Math.min(1, d / 200) * 0.00003;
          p.vx += (dx * 0.000012 - dy * swirl) * dt;
          p.vy += (dy * 0.000012 + dx * swirl) * dt;
        } else {
          // --- Bo'sh holat --------------------------------------------
          p.hx += p.hvx * dt;
          p.hy += p.hvy * dt;
          // Uy chekkadan chiqsa, zarrachaning O'ZI ham birga ko'chiriladi —
          // aks holda u ekranni kesib, uyi ortidan uchib ketardi.
          if (p.hx < 0) { p.hx += w; p.x += w; }
          else if (p.hx > w) { p.hx -= w; p.x -= w; }
          if (p.hy < 0) { p.hy += h; p.y += h; }
          else if (p.hy > h) { p.hy -= h; p.y -= h; }

          p.vx += (p.hx - p.x) * spring * dt;
          p.vy += (p.hy - p.y) * spring * dt;

          // Shakl yig'ilayotganda qolgan 70% zarracha kursorga TORTILMAYDI —
          // aks holda ular ham markazga to'planib, fon bo'shab qolardi.
          if (pointer && !forming) {
            const px = pointer.x - p.x;
            const py = pointer.y - p.y;
            const d2 = px * px + py * py;
            if (d2 < r2 && d2 > 4) {
              const d = Math.sqrt(d2);
              const f = (1 - d / pointerRadius) * pull * dt;
              p.vx += (px / d) * f;
              p.vy += (py / d) * f;
            }
          }
        }

        p.vx *= damp;
        p.vy *= damp;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (let g = 0; g < groups.length; g++) {
        ctx.fillStyle = palette[g];
        const list = groups[g];
        for (let k = 0; k < list.length; k++) {
          const p = particles[list[k]];
          ctx.fillRect(p.x, p.y, p.size, p.size);
        }
      }
    };

    let rectTick = 0;
    const render = (now: number) => {
      const dt = Math.min(50, now - last || 16);
      last = now;
      // Canvas'ning ekrandagi o'rni har ~0.5 sekundda yangilanadi: yon panel
      // ochilganda/yopilganda sichqoncha koordinatasi surilib qolmasin.
      if (++rectTick % 30 === 0) {
        const box = canvas.getBoundingClientRect();
        rect = { left: box.left, top: box.top };
      }
      forming =
        holdDelay > 0 && !!pointer && movedAt > 0 && now - movedAt > holdDelay;
      step(dt);
      draw();
      frame = requestAnimationFrame(render);
    };

    setSize();
    if (reduced) draw();
    else frame = requestAnimationFrame(render);

    // Canvas'da `pointer-events: none` (fon qatlami) — shuning uchun
    // sichqoncha oynadan tinglanadi va canvas koordinatasiga ko'chiriladi.
    const onMove = (e: PointerEvent) => {
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      // Mayda titrash "harakat" hisoblanmasin — aks holda logotip yig'ilishi
      // hech qachon boshlanmaydi.
      if (!pointer || Math.abs(x - pointer.x) > 3 || Math.abs(y - pointer.y) > 3) {
        movedAt = performance.now();
      }
      pointer = { x, y };
    };
    const onLeave = () => {
      pointer = null;
      forming = false;
    };
    if (!reduced && (attraction > 0 || holdDelay > 0)) {
      window.addEventListener("pointermove", onMove, { passive: true });
      window.addEventListener("pointerleave", onLeave);
    }

    let roTimer = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(roTimer);
      roTimer = window.setTimeout(() => {
        setSize();
        if (reduced) draw();
      }, 150);
    });
    if (canvas.parentElement) ro.observe(canvas.parentElement);
    const onWindowResize = () => {
      const box = canvas.getBoundingClientRect();
      rect = { left: box.left, top: box.top };
    };
    window.addEventListener("resize", onWindowResize);

    const onVisibility = () => {
      if (reduced) return;
      cancelAnimationFrame(frame);
      if (!document.hidden) {
        last = 0;
        frame = requestAnimationFrame(render);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(roTimer);
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("resize", onWindowResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [
    particleCount, speed, attraction, pointerRadius, holdDelay,
    logoSize, colors, opacity, isDark,
  ]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
