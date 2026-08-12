import { useEffect, useRef } from "react";

/**
 * Butun fon bo'ylab tarqalgan zarrachalar buluti: ular juda sekin suzadi va
 * sichqoncha yaqinlashganda unga tortilib, to'planadi.
 *
 * Namuna — `lightswind/cosmic-singularity-background`. U three.js/WebGL da
 * 25 000 zarracha chizadi; bu loyihada fon aynan GPU yuki sababli olib
 * tashlangan (bank kompyuterlari kuchsiz), shuning uchun bu yerda 2D
 * canvas'dagi yengil variant yozildi.
 *
 * Harakat modeli (Dekart koordinatalarida, chunki sichqonchaga tortilishni
 * qutb koordinatalarida ifodalash noqulay):
 *   1. juda zaif aylanma oqim — butun maydon sekin "nafas oladi";
 *   2. sichqoncha `pointerRadius` doirasiga kirsa — unga tomon tezlanish;
 *   3. har kadrda tezlik so'nadi (damping), shundan zarrachalar kursor
 *      atrofida to'planib qoladi va u ketgach yana tarqaladi;
 *   4. chekkadan chiqqan zarracha qarama-qarshi tomondan qaytib kiradi —
 *      shunda bulut butun fonni bir tekis qoplaydi.
 *
 * Ranglar zarrachaga TUG'ILGANDA biriktiriladi va o'zgarmaydi. Shu sababli
 * "qaysi zarracha qaysi rangda" ro'yxati bir marta tuziladi: har kadrda
 * `fillStyle` faqat ranglar soni qadar (6 marta) almashadi.
 */

interface CosmicSingularityProps {
  particleCount?: number;
  /** Umumiy tezlik ko'paytiruvchisi (1 = sekin suzish). */
  speed?: number;
  /** Sichqonchaga tortilish kuchi. 0 — o'chirilgan. */
  attraction?: number;
  /** Sichqoncha ta'sir doirasi (piksel). */
  pointerRadius?: number;
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
  /** "Uy" nuqtasi — zarracha shu joyga qaytishga intiladi. */
  hx: number;
  hy: number;
  /** Uy nuqtasining o'z sekin siljishi (px/ms). */
  hvx: number;
  hvy: number;
  size: number;
}

const LIGHT_COLORS = ["#0B5FA5", "#1A7CC8", "#5FA3D6", "#6874D6", "#2FA8A0", "#8FB8E0"];
const DARK_COLORS = ["#63B3F0", "#9ED8FF", "#5FA3D6", "#8C93E8", "#4FD1C5", "#3B82C4"];

const withAlpha = (hex: string, alpha: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha.toFixed(3)})`;
};

export default function CosmicSingularity({
  particleCount = 1400,
  speed = 1,
  attraction = 1,
  pointerRadius = 260,
  colors,
  opacity = 0.5,
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

    const particles: Particle[] = [];
    /** Rang bo'yicha guruhlangan indekslar — bir marta tuziladi. */
    const groups: number[][] = palette.map(() => []);

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
        for (let i = 0; i < particleCount; i++) {
          const x = Math.random() * w;
          const y = Math.random() * h;
          // Uy nuqtasining siljishi: 2..8 px/sek — deyarli sezilmaydigan suzish
          const ang = Math.random() * Math.PI * 2;
          const sp = (0.002 + Math.random() * 0.006) * speed;
          particles.push({
            x, y,
            vx: 0, vy: 0,
            hx: x, hy: y,
            hvx: Math.cos(ang) * sp,
            hvy: Math.sin(ang) * sp,
            size: Math.random() < 0.14 ? 2 : 1,
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
      /** Kursorga tortilish — qaytishdan ANCHA kuchli, shunda yig'ilishi
          ko'zga tashlanadi. */
      const pull = attraction * 0.0022;
      const r2 = pointerRadius * pointerRadius;
      // Damping kadr uzunligiga moslashadi. 0.90 — tez so'nadi, ya'ni
      // zarrachalar kursor atrofida "orbitaga tushmay" to'planib qoladi.
      const damp = Math.pow(0.9, dt / 16.67);

      for (const p of particles) {
        // 1) Uy nuqtasi juda sekin suzadi (chekkada o'raladi)
        p.hx += p.hvx * dt;
        p.hy += p.hvy * dt;
        // Uy chekkadan chiqsa, zarrachaning O'ZI ham birga ko'chiriladi —
        // aks holda u ekranni kesib o'tib, uyi ortidan uchib ketardi.
        if (p.hx < 0) { p.hx += w; p.x += w; }
        else if (p.hx > w) { p.hx -= w; p.x -= w; }
        if (p.hy < 0) { p.hy += h; p.y += h; }
        else if (p.hy > h) { p.hy -= h; p.y -= h; }

        // 2) Uyga tortilish
        p.vx += (p.hx - p.x) * spring * dt;
        p.vy += (p.hy - p.y) * spring * dt;

        // 3) Kursorga tortilish (yaqinroq bo'lsa — kuchliroq)
        if (pointer) {
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
      // `rect` har harakatda emas, kadr boshida yangilanadi (pastdagi
      // `render`) — canvas sahifada suriladigan element emas, lekin yon
      // panel ochilganda chap chekkasi o'zgaradi.
      pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    const onLeave = () => {
      pointer = null;
    };
    if (!reduced && attraction > 0) {
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
    const onScrollOrResize = () => {
      const box = canvas.getBoundingClientRect();
      rect = { left: box.left, top: box.top };
    };
    window.addEventListener("resize", onScrollOrResize);

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
      window.removeEventListener("resize", onScrollOrResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [particleCount, speed, attraction, pointerRadius, colors, opacity, isDark]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
