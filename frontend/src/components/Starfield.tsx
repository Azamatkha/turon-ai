import { useEffect, useRef } from "react";

/**
 * Aylanuvchi yulduzlar foni (canvas, piksel-daraja).
 *
 * Har bir yulduz markaz atrofida o'z tezligida aylanadi va ikkita sinus
 * to'lqini bilan chayqaladi. Chizish `ImageData` buferiga TO'G'RIDAN-TO'G'RI
 * piksel yozish orqali bajariladi — minglab yulduz uchun bu `arc()`
 * chaqiruvlaridan ancha arzon tushadi.
 *
 * Asl namunadan farqlar (sabablari bilan):
 *  1. `fillRect` olib tashlandi — u fonni QORA qilib bo'yardi (namunadagi
 *     sahifa qora edi). Bizda fon ochiq bo'lishi mumkin, ustiga
 *     `putImageData` pikselni baribir butunlay almashtiradi.
 *  2. Ishlatilmagan `buf`/`buf8` buferlari olib tashlandi.
 *  3. Yulduz rangi mavzuga bog'landi.
 *  4. Yulduz KATTALIGI sozlanadigan bo'ldi (`starSize`): bitta piksel juda
 *     mayda ko'rinardi, endi har yulduz kvadrat blok bilan chiziladi.
 *  5. Halqa markazi biroz tepada (`centerYRatio`) va vertikal cho'zilgan
 *     (`stretchY`) — doira emas, ellips bo'lib, logotip atrofida chiroyliroq
 *     yotadi.
 *  6. Ikkita himoya: `prefers-reduced-motion` da umuman ishlamaydi, tab
 *     fonga o'tsa to'xtaydi (bu fon ilgari CPU yuki sababli olib tashlangan).
 */

interface Star {
  orbital: number;
  opacity: number;
  position: { x: number; y: number };
  realPosition: { x: number; y: number };
  prev: { x: number; y: number };
  rSpeed: number;
  waveSpeed1: number;
  waveSpeed2: number;
  wave1: number;
  wave2: number;
}

interface StarfieldProps {
  starCount?: number;
  waveFrequency?: number;
  starEscapeWidth?: number;
  maxOpacity?: number;
  rotationSpeed?: number;
  waveSpeed?: number;
  /** Yulduz tomoni (piksel). 2 = 2x2 blok. */
  starSize?: number;
  /** Halqa markazi balandligi: 0.5 — o'rta, kichikroq qiymat — tepada. */
  centerYRatio?: number;
  /** Vertikal cho'zilish: 1 — doira, >1 — tepa-pastga cho'zilgan ellips. */
  stretchY?: number;
  isDark?: boolean;
  className?: string;
}

export default function Starfield({
  starCount = 7000,
  waveFrequency = 15,
  starEscapeWidth = 400,
  maxOpacity = 210,
  rotationSpeed = 0.0002,
  waveSpeed = 0.005,
  starSize = 3,
  centerYRatio = 0.44,
  // 1 = to'liq DUMALOQ halqa. Cho'zilgan ellips logotipni o'ramasdan,
  // pastdagi yozuv maydonining ustiga chiqib ketardi.
  stretchY = 1,
  isDark = false,
  className,
}: StarfieldProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

    const color = isDark ? { r: 255, g: 255, b: 255 } : { r: 0, g: 57, b: 120 };

    const stars: Star[] = [];
    let size = { x: 0, y: 0 };
    let cx = 0;
    let cy = 0;
    let imagedata: ImageData | null = null;
    let data: Uint32Array | null = null;
    let frame = 0;
    const startTime = Date.now();
    let currentTime = 0;

    const setSize = () => {
      const parent = canvas.parentElement;
      const next = {
        x: parent?.clientWidth || window.innerWidth,
        y: parent?.clientHeight || window.innerHeight,
      };
      // O'lcham o'zgarmagan bo'lsa — hech narsa qilmaymiz: aks holda
      // yulduzlar bekorga qaytadan tug'ilib, "miltillash" paydo bo'ladi.
      if (next.x === size.x && next.y === size.y) return;
      size = next;
      canvas.width = size.x;
      canvas.height = size.y;
      cx = size.x / 2;
      cy = size.y * centerYRatio;
      imagedata = context.createImageData(size.x, size.y);
      data = new Uint32Array(imagedata.data.buffer);
      stars.length = 0; // o'lcham o'zgarsa yulduzlar qaytadan tug'iladi
    };

    const rotate = (x: number, y: number, rad: number) => {
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);
      return {
        x: cos * (x - cx) + sin * (y - cy) + cx,
        y: cos * (y - cy) - sin * (x - cx) + cy,
      };
    };

    /** Yulduzni kvadrat blok qilib chizadi (yoki `packed = 0` bo'lsa o'chiradi). */
    const paint = (px: number, py: number, packed: number) => {
      if (!data) return;
      const x0 = Math.floor(px);
      const y0 = Math.floor(py);
      for (let dy = 0; dy < starSize; dy++) {
        const yy = y0 + dy;
        if (yy < 0 || yy >= size.y) continue;
        for (let dx = 0; dx < starSize; dx++) {
          const xx = x0 + dx;
          // Qator chegarasidan chiqib, keyingi qatorga "o'ralib" ketmasin
          if (xx < 0 || xx >= size.x) continue;
          data[yy * size.x + xx] = packed;
        }
      }
    };

    const createStar = () => {
      const orbital =
        (Math.random() * (starEscapeWidth / 2) +
          1 +
          (Math.random() * (starEscapeWidth / 2) + starEscapeWidth)) /
        2;
      const opacity = Math.floor(
        (1 - orbital / starEscapeWidth) * maxOpacity + Math.random() * 80,
      );
      const position = rotate(cx, cy + orbital, Math.PI * (Math.random() * 2));
      stars.push({
        orbital,
        opacity,
        position,
        realPosition: { ...position },
        prev: { x: -9999, y: -9999 },
        rSpeed: Math.random() * rotationSpeed + opacity / 20000,
        waveSpeed1: Math.random() * waveSpeed,
        waveSpeed2: Math.random() * waveSpeed,
        wave1: 0,
        wave2: 0,
      });
    };

    const drawStar = (star: Star) => {
      paint(star.prev.x, star.prev.y, 0); // avvalgi joyini o'chiramiz

      star.wave1 = Math.sin(currentTime * star.waveSpeed1) * waveFrequency;
      star.wave2 = Math.sin(currentTime * star.waveSpeed2) * waveFrequency;
      star.realPosition = rotate(
        star.position.x, star.position.y, star.rSpeed * currentTime,
      );
      star.opacity = Math.floor(
        (1 - star.orbital / starEscapeWidth) * maxOpacity + Math.random() * 80,
      );

      const px = star.realPosition.x + star.wave2;
      // Vertikal cho'zilish markazdan hisoblanadi
      const py = cy + (star.realPosition.y + star.wave1 - cy) * stretchY;
      star.prev = { x: px, y: py };

      // ABGR tartibida (little-endian) qadoqlanadi
      paint(px, py,
        (Math.min(255, Math.max(0, star.opacity)) << 24) |
        (color.b << 16) | (color.g << 8) | color.r);
    };

    const render = () => {
      currentTime = (Date.now() - startTime) / 10;
      if (stars.length < starCount) {
        const batch = Math.min(100, starCount - stars.length);
        for (let i = 0; i < batch; i++) createStar();
      }
      for (const star of stars) drawStar(star);
      if (imagedata) context.putImageData(imagedata, 0, 0);
      frame = requestAnimationFrame(render);
    };

    setSize();
    frame = requestAnimationFrame(render);

    const onResize = () => setSize();
    // Yon panel ochilib-yopilganda oyna o'lchami O'ZGARMAYDI — `resize`
    // hodisasi kelmaydi. Shu sababli canvas eski kenglikda qolib, halqa
    // markazi mazmun markazidan siljib ketardi. ResizeObserver ota
    // elementning haqiqiy kengligini kuzatadi va halqani qayta markazlaydi.
    // Panel kengligi animatsiya bilan o'zgargani uchun kuzatuvchi o'nlab
    // marta ishga tushadi — oxirgi holatnigina olamiz.
    let roTimer = 0;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(roTimer);
      roTimer = window.setTimeout(setSize, 150);
    });
    if (canvas.parentElement) ro.observe(canvas.parentElement);
    const onVisibility = () => {
      cancelAnimationFrame(frame);
      if (!document.hidden) frame = requestAnimationFrame(render);
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      window.clearTimeout(roTimer);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [
    starCount, waveFrequency, starEscapeWidth, maxOpacity,
    rotationSpeed, waveSpeed, starSize, centerYRatio, stretchY, isDark,
  ]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
