import { useEffect, useRef } from "react";

/**
 * Sekin aylanuvchi zarrachalar foni (canvas).
 *
 * Ilgari sahifalarda WebGL shader (GradientWaves) va DotField ishlardi —
 * ular ofis kompyuterida doimiy GPU/CPU yuki bo'lgani uchun olib tashlangan
 * edi. Bu variant ancha yengil: oddiy 2D canvas, soyalar/gradientlarsiz,
 * faqat kichik doiralar chiziladi. Ustiga ikkita himoya qo'yilgan:
 *
 *   1) `prefers-reduced-motion` yoqilgan bo'lsa — animatsiya UMUMAN
 *      ishlamaydi (foydalanuvchi harakatni xohlamagan, va bu eng arzon holat);
 *   2) tab fonga o'tsa (`document.hidden`) — halqa to'xtaydi va protsessorni
 *      bekorga bandlamaydi.
 */

interface Particle {
  radius: number;
  x: number;
  y: number;
  ring: number;
  move: number;
  angle: number;
}

interface SpaceBackgroundProps {
  /** Zarrachalar soni. Kam bo'lsa yengilroq. */
  particleCount?: number;
  /** Tungi rejimda zarrachalar oq, kunduzgida to'q bo'ladi. */
  isDark?: boolean;
  /** Joylashuvni sahifa o'zi beradi (CSS modul klassi orqali). */
  className?: string;
}

export default function SpaceBackground({
  particleCount = 320,
  isDark = false,
  className,
}: SpaceBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Harakatni kamaytirish so'ralgan bo'lsa — hech narsa chizmaymiz.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

    // Fon to'q bo'lsa yorug' zarracha, ochiq bo'lsa to'q zarracha — aks holda
    // ular fonga singib ketadi.
    const color = isDark ? "rgba(255,255,255,0.55)" : "rgba(0,57,120,0.28)";

    let frame = 0;
    let ratio = window.innerHeight < 400 ? 0.6 : 1;
    // Zarrachalar shu radiusli halqadan tashqarida aylanadi — markazda bo'sh
    // joy qoladi, ya'ni sahifa matni ustidagi qism tinch ko'rinadi.
    const innerRing = 120;
    const particles: Particle[] = [];

    const setupCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      // Koordinata boshini markazga ko'chiramiz va Y o'qini yuqoriga
      // yo'naltiramiz — aylana hisoblari shunda soddalashadi.
      ctx.setTransform(ratio, 0, 0, -ratio, canvas.width / 2, canvas.height / 2);
    };
    setupCanvas();

    for (let i = 0; i < particleCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const ring = Math.random() * innerRing * 3;
      particles.push({
        radius: Math.random() * 4 + 0.6,
        x: Math.cos(angle) * ring,
        y: Math.sin(angle) * ring,
        ring,
        move: (Math.random() * 4 + 1) / 500,
        angle,
      });
    }

    ctx.fillStyle = color;

    const step = () => {
      ctx.clearRect(
        -canvas.width, -canvas.height, canvas.width * 2, canvas.height * 2,
      );
      for (const p of particles) {
        // Kichrayib borgan zarracha qaytadan tashqi halqada tug'iladi —
        // shunda oqim uzluksiz ko'rinadi.
        if (p.radius < 0.8) {
          p.ring = Math.random() * innerRing * 3;
          p.radius = Math.random() * 4 + 0.6;
        }
        p.radius *= 0.994;
        p.ring = Math.max(p.ring - 1, innerRing);
        p.angle += p.move;
        p.x = Math.cos(p.angle) * p.ring;
        p.y = Math.sin(p.angle) * p.ring;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);

    const onResize = () => {
      ratio = window.innerHeight < 400 ? 0.6 : 1;
      setupCanvas();
      ctx.fillStyle = color;
    };
    // Tab fonga o'tganda halqani to'xtatamiz — brauzer o'zi ham sekinlashtiradi,
    // lekin bu kafolatli.
    const onVisibility = () => {
      cancelAnimationFrame(frame);
      if (!document.hidden) frame = requestAnimationFrame(step);
    };

    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [particleCount, isDark]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
