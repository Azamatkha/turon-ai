import { useEffect, useRef, type ReactNode } from "react";
import styles from "./StarBorder.module.css";

// Tugma chetidan aylanib yuradigan "yulduz" nuri (canvas). react-bits
// StarBorder'idan moslashtirilgan: bu yerda u O'ROVCHI — ichidagi tugma
// (o'z stili, tooltip, menyusi bilan) o'zgarmaydi, nur ustidan chiziladi.
// Tashqi kutubxona yo'q. Ichkaridagi eski `.tu-shiny` ramkasi o'chiriladi
// (ikki effekt ustma-ust tushmasin).

type Rgb = [number, number, number];
type Segment = { length: number; x: number; y: number; dx: number; dy: number; angle: number | null };
type Shape = { r: number; segments: Segment[]; total: number };
type Point = { x: number; y: number; nx: number; ny: number };
type Pulse = { origin: number; age: number };
type Mote = { x: number; y: number; vx: number; vy: number; age: number; life: number; size: number; seed: number };
type Settings = {
  light: boolean;
  color: string;
  trailColor: string;
  duration: number;
  thickness: number;
  radius: number;
  trailLength: number;
  stars: number;
  glow: number;
  sparkle: boolean;
  direction: number;
  clickPulse: boolean;
};

interface StarBorderProps {
  children: ReactNode;
  color: string;
  trailColor?: string;
  theme?: "dark" | "light";
  duration?: number;
  thickness?: number;
  radius?: number;
  trailLength?: number;
  stars?: number;
  glow?: number;
  sparkle?: boolean;
  direction?: "clockwise" | "counterclockwise";
  clickPulse?: boolean;
  className?: string;
}

const BLEED = 48;
const TAU = Math.PI * 2;
const WHITE: Rgb = [255, 255, 255];

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));
const wrap = (v: number, total: number) => ((v % total) + total) % total;
const mix = (a: Rgb, b: Rgb, t: number): Rgb => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const rgba = (c: Rgb, a: number) =>
  `rgba(${Math.round(c[0])}, ${Math.round(c[1])}, ${Math.round(c[2])}, ${clamp(a, 0, 1).toFixed(3)})`;

let colorCtx: CanvasRenderingContext2D | null = null;
const toRgb = (color: string): Rgb => {
  colorCtx = colorCtx ?? document.createElement("canvas").getContext("2d");
  if (!colorCtx) return WHITE;
  colorCtx.fillStyle = "#000000";
  colorCtx.fillStyle = color;
  const v = String(colorCtx.fillStyle);
  if (v.startsWith("#")) {
    const hex = parseInt(v.slice(1, 7), 16);
    return [(hex >> 16) & 255, (hex >> 8) & 255, hex & 255];
  }
  const p = v.match(/[\d.]+/g)?.map(Number) ?? WHITE;
  return [p[0], p[1], p[2]];
};

const outline = (w: number, h: number, radius: number): Shape => {
  const r = Math.max(0, Math.min(radius, w / 2, h / 2));
  const arc = (Math.PI * r) / 2;
  const across = Math.max(0, w - 2 * r);
  const down = Math.max(0, h - 2 * r);
  const segments: Segment[] = [
    { length: across, x: r, y: 0, dx: 1, dy: 0, angle: null },
    { length: arc, x: w - r, y: r, dx: 0, dy: 0, angle: -Math.PI / 2 },
    { length: down, x: w, y: r, dx: 0, dy: 1, angle: null },
    { length: arc, x: w - r, y: h - r, dx: 0, dy: 0, angle: 0 },
    { length: across, x: w - r, y: h, dx: -1, dy: 0, angle: null },
    { length: arc, x: r, y: h - r, dx: 0, dy: 0, angle: Math.PI / 2 },
    { length: down, x: 0, y: h - r, dx: 0, dy: -1, angle: null },
    { length: arc, x: r, y: r, dx: 0, dy: 0, angle: Math.PI },
  ];
  return { r, segments, total: Math.max(1, segments.reduce((s, g) => s + g.length, 0)) };
};

const pointAt = (shape: Shape, distance: number, pt: Point) => {
  let s = wrap(distance, shape.total);
  for (const g of shape.segments) {
    if (g.length > 0 && s <= g.length) {
      if (g.angle === null) {
        pt.x = g.x + g.dx * s;
        pt.y = g.y + g.dy * s;
        pt.nx = g.dy;
        pt.ny = -g.dx;
      } else {
        const a = g.angle + s / shape.r;
        pt.nx = Math.cos(a);
        pt.ny = Math.sin(a);
        pt.x = g.x + pt.nx * shape.r;
        pt.y = g.y + pt.ny * shape.r;
      }
      return pt;
    }
    s -= g.length;
  }
  return pt;
};

// Kursor turgan nuqtaga eng yaqin kontur masofasi (bosilganda impuls shu yerdan)
const project = (shape: Shape, px: number, py: number) => {
  let best = Infinity;
  let found = 0;
  let offset = 0;
  shape.segments.forEach((g) => {
    if (g.length > 0) {
      let s: number, x: number, y: number;
      if (g.angle === null) {
        s = clamp((px - g.x) * g.dx + (py - g.y) * g.dy, 0, g.length);
        x = g.x + g.dx * s;
        y = g.y + g.dy * s;
      } else {
        let a = wrap(Math.atan2(py - g.y, px - g.x) - g.angle, TAU);
        if (a > Math.PI / 2) a = a > Math.PI * 1.25 ? 0 : Math.PI / 2;
        s = a * shape.r;
        x = g.x + Math.cos(g.angle + a) * shape.r;
        y = g.y + Math.sin(g.angle + a) * shape.r;
      }
      const d = (px - x) ** 2 + (py - y) ** 2;
      if (d < best) {
        best = d;
        found = offset + s;
      }
    }
    offset += g.length;
  });
  return found;
};

export default function StarBorder({
  children,
  color,
  trailColor,
  theme = "dark",
  // Navbar uchun YUMSHOQ standart: bitta ingichka nur, uchqunsiz, sekin.
  // (2 yulduz + qalin + uchqun kichik tugmalarda juda bejirim ko'rinardi.)
  duration = 6,
  thickness = 1.5,
  radius = 12,
  trailLength = 0.35,
  stars = 1,
  glow = 0.35,
  sparkle = false,
  direction = "clockwise",
  clickPulse = true,
  className = "",
}: StarBorderProps) {
  const rootRef = useRef<HTMLSpanElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wakeRef = useRef<(() => void) | null>(null);
  const settings: Settings = {
    light: theme === "light",
    color,
    trailColor: trailColor ?? color,
    duration: Math.max(0.3, duration),
    thickness: Math.max(0.5, thickness),
    radius: Math.max(0, radius),
    trailLength: clamp(trailLength, 0, 1),
    stars: clamp(Math.round(stars), 1, 6),
    glow: clamp(glow, 0, 1),
    sparkle,
    direction: direction === "counterclockwise" ? -1 : 1,
    clickPulse,
  };
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    const root = rootRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!root || !canvas || !ctx) return undefined;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const pt: Point = { x: 0, y: 0, nx: 0, ny: -1 };
    const st = {
      width: 0, height: 0, dpr: 1, phase: 0, velocity: 0, motion: 0, time: 0,
      boost: 0, flash: 0, emit: 0, hovered: false, focused: false, visible: true,
    };
    const pulses: Pulse[] = [];
    const dust: Mote[] = [];
    const colors = { key: "", head: WHITE, tail: WHITE };
    let raf = 0;
    let last = performance.now();
    let alive = true;

    const measure = () => {
      st.width = root.offsetWidth;
      st.height = root.offsetHeight;
      st.dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round((st.width + BLEED * 2) * st.dpr));
      canvas.height = Math.max(1, Math.round((st.height + BLEED * 2) * st.dpr));
      wake();
    };

    const local = (e: MouseEvent): [number, number] => {
      const r = root.getBoundingClientRect();
      return [e.clientX - r.left, e.clientY - r.top];
    };

    const shapeFor = (s: Settings) =>
      outline(Math.max(1, st.width - s.thickness), Math.max(1, st.height - s.thickness), s.radius - s.thickness / 2);

    const stroke = (x1: number, y1: number, x2: number, y2: number, w: number, style: string | CanvasGradient) => {
      ctx.lineWidth = w;
      ctx.strokeStyle = style;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    };

    const drawTrail = (s: Settings, shape: Shape, head: number, length: number, sign: number, intensity: number, tip = true) => {
      if (length < 0.5 || intensity <= 0) return;
      const steps = clamp(Math.ceil(length / 2), 2, 90);
      pointAt(shape, head, pt);
      let px = pt.x;
      let py = pt.y;
      for (let i = 1; i <= steps; i++) {
        pointAt(shape, head - sign * length * (i / steps), pt);
        const u = 1 - (i - 0.5) / steps;
        const fade = u * u * intensity;
        let tone = mix(colors.tail, colors.head, u);
        if (!s.light) tone = mix(tone, WHITE, u ** 6 * 0.65);
        ctx.lineCap = tip && i === 1 ? "round" : "butt";
        stroke(px, py, pt.x, pt.y, 2 + 6 * s.glow, rgba(tone, fade * (s.light ? 0.1 : 0.2) * s.glow));
        stroke(px, py, pt.x, pt.y, s.thickness, rgba(tone, fade));
        px = pt.x;
        py = pt.y;
      }
    };

    const drawHead = (s: Settings, x: number, y: number, intensity: number, twinkle: number) => {
      if (intensity <= 0) return;
      const tone = colors.head;
      const reach = (12 + 40 * s.glow) * (s.light ? 0.6 : 1);
      const bloom = ctx.createRadialGradient(x, y, 0, x, y, reach);
      const strength = (s.light ? 0.08 : 0.4) * s.glow * intensity;
      bloom.addColorStop(0, rgba(tone, strength));
      bloom.addColorStop(0.2, rgba(tone, strength * 0.4));
      bloom.addColorStop(0.5, rgba(tone, strength * 0.1));
      bloom.addColorStop(1, rgba(tone, 0));
      ctx.fillStyle = bloom;
      ctx.fillRect(x - reach, y - reach, reach * 2, reach * 2);
      if (!s.sparkle) return;

      const size = (1 + s.thickness * 0.6) * (s.light ? 0.85 : 1);
      const core = ctx.createRadialGradient(x, y, 0, x, y, size * 2.2);
      core.addColorStop(0, rgba(s.light ? tone : WHITE, intensity));
      core.addColorStop(s.light ? 0.3 : 0.4, rgba(s.light ? tone : mix(tone, WHITE, 0.5), intensity * 0.9));
      core.addColorStop(s.light ? 0.55 : 1, rgba(tone, s.light ? intensity * 0.12 : 0));
      core.addColorStop(1, rgba(tone, 0));
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(x, y, size * 2.2, 0, TAU);
      ctx.fill();

      const spike = (3 + 4 * s.glow + s.thickness * 1.5) * twinkle;
      const center = s.light ? tone : WHITE;
      const hz = ctx.createLinearGradient(x - spike, y, x + spike, y);
      hz.addColorStop(0, rgba(tone, 0));
      hz.addColorStop(0.5, rgba(center, intensity * 0.95));
      hz.addColorStop(1, rgba(tone, 0));
      stroke(x - spike, y, x + spike, y, s.light ? 0.75 : 1, hz);
      const vt = ctx.createLinearGradient(x, y - spike, x, y + spike);
      vt.addColorStop(0, rgba(tone, 0));
      vt.addColorStop(0.5, rgba(center, intensity * 0.95));
      vt.addColorStop(1, rgba(tone, 0));
      stroke(x, y - spike, x, y + spike, s.light ? 0.75 : 1, vt);
    };

    const spawnDust = (x: number, y: number, nx: number, ny: number, speed: number) => {
      if (dust.length > 48) return;
      const push = 3 + Math.random() * 10;
      const drift = (Math.random() - 0.5) * 8;
      dust.push({
        x: x + nx * (Math.random() * 3 - 1),
        y: y + ny * (Math.random() * 3 - 1),
        vx: nx * push - ny * drift - speed * -ny * 0.04,
        vy: ny * push + nx * drift - speed * nx * 0.04,
        age: 0,
        life: 0.35 + Math.random() * 0.5,
        size: 0.45 + Math.random() * 0.7,
        seed: Math.random() * TAU,
      });
    };

    const draw = (base: Settings, shape: Shape) => {
      const s = st.boost > 0.001 ? { ...base, glow: Math.min(1.5, base.glow + 0.4 * st.boost) } : base;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (st.width < 2 || st.height < 2) return;
      const off = (BLEED + s.thickness / 2) * st.dpr;
      ctx.setTransform(st.dpr, 0, 0, st.dpr, off, off);
      ctx.globalCompositeOperation = s.light ? "source-over" : "lighter";
      ctx.lineCap = "butt";

      const total = shape.total;
      const spacing = total / s.stars;
      const speed = Math.abs(st.motion);
      const sign = st.motion >= 0 ? 1 : -1;
      const length = Math.min(speed * s.trailLength * s.duration, spacing * 0.92, total * 0.6);
      const intensity = 1 + 0.4 * st.boost + 0.6 * st.flash;

      const ring = st.flash * (s.light ? 0.18 : 0.32) + st.boost * (s.light ? 0.07 : 0.12);
      if (ring > 0.005) {
        ctx.lineWidth = s.thickness + 2 * s.glow;
        ctx.strokeStyle = rgba(colors.head, ring);
        ctx.beginPath();
        ctx.roundRect(0, 0, Math.max(1, st.width - s.thickness), Math.max(1, st.height - s.thickness), Math.max(0, shape.r));
        ctx.stroke();
      }

      for (let i = 0; i < s.stars; i++) {
        drawTrail(s, shape, st.phase + i * spacing, length, sign, Math.min(1, intensity));
      }

      pulses.forEach((p) => {
        const fade = (1 - p.age / 0.65) ** 2;
        const travel = (total / 2) * (1 - (1 - Math.min(1, p.age / 0.5)) ** 2);
        const tail = Math.min(travel, total * 0.16);
        [1, -1].forEach((way) => {
          const front = p.origin + way * travel;
          drawTrail(s, shape, front, tail, way, fade);
          pointAt(shape, front, pt);
          drawHead(s, pt.x, pt.y, fade * 0.8, 0.8);
        });
      });

      for (let i = 0; i < s.stars; i++) {
        pointAt(shape, st.phase + i * spacing, pt);
        const twinkle = 0.82 + 0.18 * Math.sin(st.time * 6.1 + i * 2.3) * Math.sin(st.time * 2.7 + i);
        drawHead(s, pt.x, pt.y, Math.min(1.3, intensity), twinkle);
      }

      dust.forEach((m) => {
        const left = 1 - m.age / m.life;
        const shimmer = 0.45 + 0.55 * Math.sin(st.time * 20 + m.seed);
        const alpha = left * shimmer * (s.light ? 0.35 : 0.9);
        if (alpha <= 0.01) return;
        ctx.fillStyle = rgba(s.light ? colors.head : mix(colors.tail, WHITE, 0.6), alpha);
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.size * (0.6 + 0.4 * left), 0, TAU);
        ctx.fill();
      });
    };

    const frame = (now: number) => {
      raf = 0;
      if (!alive) return;
      const s = settingsRef.current;
      const dt = Math.min(0.05, Math.max(0.001, (now - last) / 1000));
      last = now;
      st.time += dt;

      const key = `${s.color}|${s.trailColor}`;
      if (key !== colors.key) {
        colors.key = key;
        colors.head = toRgb(s.color);
        colors.tail = toRgb(s.trailColor);
      }

      const shape = shapeFor(s);
      const total = shape.total;
      const spacing = total / s.stars;
      const engaged = st.hovered || st.focused;
      const cruise = reduce ? 0 : (s.direction * total) / s.duration;

      // hover="brighten" — kursor ustida nur yorqinroq
      const boostTarget = engaged ? 1 : 0;
      st.boost += (boostTarget - st.boost) * (1 - Math.exp(-dt / (boostTarget > st.boost ? 0.18 : 0.5)));
      st.flash *= Math.exp(-dt / 0.22);

      st.velocity += (cruise - st.velocity) * (1 - Math.exp(-dt / 0.45));
      st.motion = st.velocity;
      st.phase = wrap(st.phase + st.velocity * dt, total);

      if (s.sparkle && !reduce) {
        st.emit += dt * 4 * s.stars;
        while (st.emit > 1) {
          st.emit -= 1;
          pointAt(shape, st.phase + Math.floor(Math.random() * s.stars) * spacing, pt);
          spawnDust(pt.x, pt.y, pt.nx, pt.ny, st.motion);
        }
      }
      for (let i = dust.length - 1; i >= 0; i--) {
        const m = dust[i];
        m.age += dt;
        m.x += m.vx * dt;
        m.y += m.vy * dt;
        m.vx *= Math.exp(-dt * 2.2);
        m.vy *= Math.exp(-dt * 2.2);
        if (m.age >= m.life) dust.splice(i, 1);
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        pulses[i].age += dt;
        if (pulses[i].age >= 0.65) pulses.splice(i, 1);
      }

      draw(s, shape);

      const settling = Math.abs(boostTarget - st.boost) > 0.002 || st.flash > 0.01 || pulses.length > 0 || dust.length > 0;
      const moving = Math.abs(st.motion) > 0.05 || cruise !== 0;
      // Ko'rinmasa (tab yashirin, ekrandan tashqarida) — kadr chizilmaydi
      if (st.visible && !document.hidden && (settling || moving || st.hovered)) raf = requestAnimationFrame(frame);
    };

    const wake = () => {
      if (raf || !alive || !st.visible) return;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };
    wakeRef.current = wake;

    const onEnter = () => { st.hovered = true; wake(); };
    const onLeave = () => { st.hovered = false; wake(); };
    const pulse = (origin: number) => {
      if (!settingsRef.current.clickPulse) return;
      pulses.push({ origin, age: 0 });
      if (pulses.length > 4) pulses.shift();
      st.flash = 1;
      wake();
    };
    const onDown = (e: PointerEvent) => {
      if (e.button !== 0 && e.pointerType === "mouse") return;
      const s = settingsRef.current;
      const [x, y] = local(e);
      pulse(project(shapeFor(s), x - s.thickness / 2, y - s.thickness / 2));
    };
    // Ichidagi tugma fokus oladi — focus emas, focusin/focusout (ko'tariladi)
    const onFocusIn = () => {
      st.focused = !!root.querySelector(":focus-visible");
      wake();
    };
    const onFocusOut = () => { st.focused = false; wake(); };
    const onVisibility = () => wake();

    const ro = new ResizeObserver(measure);
    ro.observe(root);
    const io = new IntersectionObserver((entries) => {
      st.visible = entries.some((e) => e.isIntersecting);
      if (st.visible) wake();
    });
    io.observe(root);
    root.addEventListener("pointerenter", onEnter);
    root.addEventListener("pointerleave", onLeave);
    root.addEventListener("pointerdown", onDown);
    root.addEventListener("focusin", onFocusIn);
    root.addEventListener("focusout", onFocusOut);
    document.addEventListener("visibilitychange", onVisibility);
    measure();

    return () => {
      alive = false;
      wakeRef.current = null;
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      root.removeEventListener("pointerenter", onEnter);
      root.removeEventListener("pointerleave", onLeave);
      root.removeEventListener("pointerdown", onDown);
      root.removeEventListener("focusin", onFocusIn);
      root.removeEventListener("focusout", onFocusOut);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  useEffect(() => {
    wakeRef.current?.();
  });

  return (
    <span ref={rootRef} className={`${styles.root} ${className}`} style={{ borderRadius: settings.radius }}>
      {children}
      <canvas ref={canvasRef} className={styles.light} aria-hidden="true" />
    </span>
  );
}
