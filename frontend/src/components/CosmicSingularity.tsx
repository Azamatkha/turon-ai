import { useEffect, useRef } from "react";

/**
 * "Kosmik singulyarlik" foni: markaz atrofida aylanib, sekin ichkariga
 * tortiladigan zarrachalar buluti.
 *
 * Namuna sifatida `lightswind/cosmic-singularity-background` olingan, lekin
 * u WebGL (three.js) da 25 000 zarracha chizadi. Bu loyihada fon ilgari
 * aynan GPU yuki sababli olib tashlangan (bank kompyuterlari kuchsiz), shu
 * bois bu yerda 2D canvas'dagi yengil variant yozildi:
 *
 *  - zarrachalar soni ~1600 (WebGL emas, lekin ko'z uchun farqi kam);
 *  - rang RADIUS bo'yicha `colorInner` va `colorOuter` orasida aralashadi,
 *    lekin har kadrda 1600 marta `fillStyle` almashtirmaslik uchun ranglar
 *    oldindan 10 ta "chelak"ka bo'lingan va chizish shu chelaklar bo'yicha
 *    guruhlab bajariladi;
 *  - burchak tezligi radiusga teskari (Kepler qonuniga o'xshash): ichkaridagi
 *    zarrachalar tezroq aylanadi, shundan "burama" hosil bo'ladi;
 *  - markazga yetgan zarracha tashqi chekkada qayta tug'iladi;
 *  - `prefers-reduced-motion` da bir marta chizib to'xtaydi, tab fonga
 *    o'tsa animatsiya butunlay to'xtaydi.
 */

interface CosmicSingularityProps {
  /** Zarrachalar soni. */
  particleCount?: number;
  /** Aylanish tezligi ko'paytiruvchisi. */
  speed?: number;
  /** Markazga tortilish tezligi. */
  gravity?: number;
  /** Markazdagi rang (hex). */
  colorInner?: string;
  /** Chetdagi rang (hex). */
  colorOuter?: string;
  /** Umumiy shaffoflik. */
  opacity?: number;
  isDark?: boolean;
  className?: string;
}

interface Particle {
  /** Markazdan masofa (0..1, canvas o'lchamiga nisbatan). */
  r: number;
  /** Burchak (radian). */
  a: number;
  /** Individual tezlik tarqoqligi. */
  jitter: number;
  size: number;
}

const hexToRgb = (hex: string) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
};

/** Chelaklar soni: rang shu qadar bosqichda o'zgaradi. */
const BUCKETS = 10;

export default function CosmicSingularity({
  particleCount = 1600,
  speed = 1,
  gravity = 1,
  colorInner,
  colorOuter,
  opacity = 0.55,
  isDark = false,
  className,
}: CosmicSingularityProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const inner = hexToRgb(colorInner ?? (isDark ? "#9ED8FF" : "#5FA3D6"));
    const outer = hexToRgb(colorOuter ?? (isDark ? "#0B5FA5" : "#003978"));

    // Rang chelaklari: markazdan chetga qarab aralashma
    const palette = Array.from({ length: BUCKETS }, (_, i) => {
      const t = i / (BUCKETS - 1);
      const r = Math.round(inner.r + (outer.r - inner.r) * t);
      const g = Math.round(inner.g + (outer.g - inner.g) * t);
      const b = Math.round(inner.b + (outer.b - inner.b) * t);
      // Chetga borgan sari xiraroq
      const alpha = opacity * (1 - t * 0.55);
      return `rgba(${r},${g},${b},${alpha.toFixed(3)})`;
    });

    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let cx = 0;
    let cy = 0;
    /** Halqa radiusi piksel o'lchovida — canvas o'lchamiga bog'lanadi. */
    let scale = 0;
    let frame = 0;
    let last = 0;

    const particles: Particle[] = [];
    const buckets: number[][] = Array.from({ length: BUCKETS }, () => []);

    const spawn = (p: Particle, fresh: boolean) => {
      // `fresh` — birinchi to'ldirish: butun maydonga tarqatiladi.
      p.r = fresh ? 0.12 + Math.random() * 0.88 : 0.9 + Math.random() * 0.25;
      p.a = Math.random() * Math.PI * 2;
      p.jitter = 0.6 + Math.random() * 0.8;
      p.size = Math.random() < 0.12 ? 2 : 1;
    };

    for (let i = 0; i < particleCount; i++) {
      const p: Particle = { r: 0, a: 0, jitter: 1, size: 1 };
      spawn(p, true);
      particles.push(p);
    }

    const setSize = () => {
      const parent = canvas.parentElement;
      const nw = parent?.clientWidth || window.innerWidth;
      const nh = parent?.clientHeight || window.innerHeight;
      if (nw === w && nh === h) return;
      w = nw;
      h = nh;
      canvas.width = w;
      canvas.height = h;
      cx = w / 2;
      // Halqa markazi biroz tepada — logotip va orbitalar bilan bir joyda
      cy = h * 0.44;
      scale = Math.min(w, h) * 0.46;
    };

    const draw = (dt: number) => {
      ctx.clearRect(0, 0, w, h);
      for (const list of buckets) list.length = 0;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        // Ichkaridagilar tezroq aylanadi -> burama shakl
        p.a += ((0.00022 * speed * p.jitter) / (p.r * p.r + 0.05)) * dt;
        p.r -= 0.000004 * gravity * p.jitter * dt;
        if (p.r < 0.1) spawn(p, false);

        const idx = Math.min(BUCKETS - 1, Math.max(0, Math.floor(p.r * BUCKETS)));
        buckets[idx].push(i);
      }

      for (let b = 0; b < BUCKETS; b++) {
        const list = buckets[b];
        if (!list.length) continue;
        ctx.fillStyle = palette[b];
        for (let k = 0; k < list.length; k++) {
          const p = particles[list[k]];
          const rad = p.r * scale;
          const x = cx + Math.cos(p.a) * rad;
          const y = cy + Math.sin(p.a) * rad;
          if (x < 0 || y < 0 || x >= w || y >= h) continue;
          ctx.fillRect(x, y, p.size, p.size);
        }
      }
    };

    const render = (now: number) => {
      const dt = Math.min(50, now - last || 16);
      last = now;
      draw(dt);
      frame = requestAnimationFrame(render);
    };

    setSize();
    if (reduced) {
      draw(0);
    } else {
      frame = requestAnimationFrame(render);
    }

    // Yon panel ochilganda oyna o'lchami o'zgarmaydi — ota elementni kuzatamiz
    let roTimer = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(roTimer);
      roTimer = window.setTimeout(() => {
        setSize();
        if (reduced) draw(0);
      }, 150);
    });
    if (canvas.parentElement) ro.observe(canvas.parentElement);

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
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [particleCount, speed, gravity, colorInner, colorOuter, opacity, isDark]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
