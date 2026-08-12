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
          particles.push({
            x: Math.random() * w,
            y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.01,
            vy: (Math.random() - 0.5) * 0.01,
            size: Math.random() < 0.14 ? 2 : 1,
          });
          groups[i % groups.length].push(i);
        }
      } else {
        // O'lcham o'zgarsa zarrachalar nisbatan joyida qolsin
        for (const p of particles) {
          p.x *= sx;
          p.y *= sy;
        }
      }
    };

    const step = (dt: number) => {
      const cx = w / 2;
      const cy = h / 2;
      // Sekin aylanma oqim: markazdan uzoqlashgan sari biroz kuchliroq
      const swirl = 0.0000012 * speed;
      const pull = attraction * 0.00006;
      const r2 = pointerRadius * pointerRadius;
      // Damping kadr uzunligiga moslashadi (60 fps da ~0.988)
      const damp = Math.pow(0.988, dt / 16.67);

      for (const p of particles) {
        const dx = p.x - cx;
        const dy = p.y - cy;
        // Perpendikulyar tezlanish — aylanma oqim
        p.vx += -dy * swirl * dt;
        p.vy += dx * swirl * dt;

        if (pointer) {
          const px = pointer.x - p.x;
          const py = pointer.y - p.y;
          const d2 = px * px + py * py;
          if (d2 < r2 && d2 > 1) {
            // Yaqinroq bo'lsa — kuchliroq tortiladi
            const f = (1 - Math.sqrt(d2) / pointerRadius) * pull * dt;
            const inv = 1 / Math.sqrt(d2);
            p.vx += px * inv * f;
            p.vy += py * inv * f;
          }
        }

        p.vx *= damp;
        p.vy *= damp;
        p.x += p.vx * dt;
        p.y += p.vy * dt;

        // Chekkadan chiqqani qarama-qarshi tomondan kiradi
        if (p.x < -2) p.x += w + 4;
        else if (p.x > w + 2) p.x -= w + 4;
        if (p.y < -2) p.y += h + 4;
        else if (p.y > h + 2) p.y -= h + 4;
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

    const render = (now: number) => {
      const dt = Math.min(50, now - last || 16);
      last = now;
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
