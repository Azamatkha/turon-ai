import { useEffect, useRef } from "react";

import "./NeuralBackground.css";

// Oqim maydoni (flow field) zarrachalari — kursordan qochadigan, iz qoldiradigan
// nuqtalar. Chat sahifasida gradient fon USTIDA ishlatiladi.
//
// ASL KODDAN IKKI FARQ:
//  1) Tailwind (`cn`, `bg-black`) o'rniga oddiy CSS — loyihada Tailwind yo'q.
//  2) Iz (trail) effekti qora bilan emas, `destination-out` bilan chiziladi:
//     kanva SHAFFOF qoladi, shuning uchun ostidagi gradient ko'rinib turadi.
//     Asl variant har kadrda rgba(0,0,0,...) bilan bo'yab, light rejimda
//     sahifani qoraytirib yuborardi.

interface NeuralBackgroundProps {
  className?: string;
  /** Zarrachalar rangi. */
  color?: string;
  /** Iz shaffofligi (0..1). Kichik = uzun iz, katta = kalta iz. */
  trailOpacity?: number;
  /** Zarrachalar soni. */
  particleCount?: number;
  /** Tezlik koeffitsienti. */
  speed?: number;
}

export default function NeuralBackground({
  className,
  color = "#6366f1",
  trailOpacity = 0.15,
  particleCount = 600,
  speed = 1,
}: NeuralBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = container.clientWidth;
    let height = container.clientHeight;
    let particles: Particle[] = [];
    let animationFrameId: number;
    const mouse = { x: -1000, y: -1000 };

    class Particle {
      x = 0;
      y = 0;
      vx = 0;
      vy = 0;
      age = 0;
      life = 0;

      constructor() {
        this.reset();
      }

      update() {
        // Oqim maydoni: joylashuvga qarab burchak hisoblanadi.
        const angle =
          (Math.cos(this.x * 0.005) + Math.sin(this.y * 0.005)) * Math.PI;

        this.vx += Math.cos(angle) * 0.2 * speed;
        this.vy += Math.sin(angle) * 0.2 * speed;

        // Kursordan qochish.
        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const interactionRadius = 150;

        if (distance < interactionRadius) {
          const force = (interactionRadius - distance) / interactionRadius;
          this.vx -= dx * force * 0.05;
          this.vy -= dy * force * 0.05;
        }

        this.x += this.vx;
        this.y += this.vy;
        // Ishqalanish — cheksiz tezlanishning oldini oladi.
        this.vx *= 0.95;
        this.vy *= 0.95;

        this.age++;
        if (this.age > this.life) {
          this.reset();
        }

        // Ekran chetidan o'tsa — qarama-qarshi tomondan chiqadi.
        if (this.x < 0) this.x = width;
        if (this.x > width) this.x = 0;
        if (this.y < 0) this.y = height;
        if (this.y > height) this.y = 0;
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = 0;
        this.vy = 0;
        this.age = 0;
        this.life = Math.random() * 200 + 100;
      }

      draw(context: CanvasRenderingContext2D) {
        context.fillStyle = color;
        // Yoshiga qarab paydo bo'lib, so'ng so'nadi.
        const alpha = 1 - Math.abs(this.age / this.life - 0.5) * 2;
        context.globalAlpha = alpha;
        context.fillRect(this.x, this.y, 1.5, 1.5);
      }
    }

    const init = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      // setTransform (scale emas) — resize'da o'lchov ustma-ust ko'paymasin.
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      particles = [];
      for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
      }
    };

    const animate = () => {
      // Iz effekti: kanvani bo'yamaymiz, balki asta-sekin O'CHIRAMIZ —
      // shunda kanva shaffof qoladi va ostidagi fon ko'rinib turadi.
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = `rgba(0, 0, 0, ${trailOpacity})`;
      ctx.fillRect(0, 0, width, height);
      ctx.globalCompositeOperation = "source-over";

      particles.forEach((p) => {
        p.update();
        p.draw(ctx);
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    const handleResize = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      init();
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    init();
    animate();

    window.addEventListener("resize", handleResize);
    // Qatlamda pointer-events: none bo'lishi mumkin — shuning uchun kursorni
    // window'dan kuzatamiz, aks holda qochish effekti umuman ishlamaydi.
    window.addEventListener("mousemove", handleMouseMove);
    container.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      container.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, [color, trailOpacity, particleCount, speed]);

  return (
    <div
      ref={containerRef}
      className={`neural-background-container ${className ?? ""}`.trim()}
    >
      <canvas ref={canvasRef} className="neural-background-canvas" />
    </div>
  );
}
