import { useEffect, useRef } from "react";

/**
 * Aylanuvchi yulduzlar foni (canvas, piksel-daraja).
 *
 * Har bir yulduz markaz atrofida o'z tezligida aylanadi va ikkita sinus
 * to'lqini bilan chayqaladi. Chizish `ImageData` buferiga TO'G'RIDAN-TO'G'RI
 * piksel yozish orqali bajariladi — shuning uchun minglab yulduz bo'lsa ham
 * `arc()` chaqiruvlaridan ancha arzon tushadi.
 *
 * Asl namunadan farqlar (sabablari bilan):
 *  1. `fillRect` olib tashlandi. Namunada u fonni QORA qilib bo'yardi
 *     (u yerda sahifa ham qora edi). Bizda fon ochiq bo'lishi mumkin, ustiga
 *     `putImageData` baribir pikselni butunlay almashtiradi — ya'ni u qatorning
 *     foydasi yo'q, zarari bor edi.
 *  2. Ishlatilmagan `buf`/`buf8` buferlari olib tashlandi.
 *  3. Yulduz rangi mavzuga bog'landi (tungi rejimda yorug', kunduzgida to'q).
 *  4. Ikkita himoya qo'shildi: `prefers-reduced-motion` yoqilgan bo'lsa
 *     animatsiya umuman ishlamaydi, tab fonga o'tsa halqa to'xtaydi. Bu fon
 *     ilgari "ofis kompyuterida doimiy CPU yuki" deb olib tashlangan edi.
 */

interface Star {
  orbital: number;
  opacity: number;
  position: { x: number; y: number };
  realPosition: { x: number; y: number };
  rotation: number;
  rSpeed: number;
  waveSpeed1: number;
  waveSpeed2: number;
  wave1: number;
  wave2: number;
}

interface StarfieldProps {
  /** Yulduzlar soni. Ko'p bo'lsa zichroq, lekin og'irroq. */
  starCount?: number;
  /** Chayqalish kuchi (piksel). */
  waveFrequency?: number;
  /** Yulduzlar tarqaladigan radius. */
  starEscapeWidth?: number;
  maxOpacity?: number;
  rotationSpeed?: number;
  waveSpeed?: number;
  /** Tungi rejimda yulduzlar oq, kunduzgida brend ko'ki bo'ladi. */
  isDark?: boolean;
  /** Joylashuvni sahifa beradi (CSS modul klassi). */
  className?: string;
}

export default function Starfield({
  starCount = 6000,
  waveFrequency = 15,
  starEscapeWidth = 400,
  maxOpacity = 190,
  rotationSpeed = 0.0002,
  waveSpeed = 0.005,
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

    // Tungi fonda oq, ochiq fonda brend ko'ki (#003978).
    const color = isDark ? { r: 255, g: 255, b: 255 } : { r: 0, g: 57, b: 120 };

    const stars: Star[] = [];
    let size = { x: 0, y: 0 };
    let imagedata: ImageData | null = null;
    let data: Uint32Array | null = null;
    let frame = 0;
    const startTime = Date.now();
    let currentTime = 0;

    const setSize = () => {
      const parent = canvas.parentElement;
      size = {
        x: parent?.clientWidth || window.innerWidth,
        y: parent?.clientHeight || window.innerHeight,
      };
      canvas.width = size.x;
      canvas.height = size.y;
      imagedata = context.createImageData(size.x, size.y);
      data = new Uint32Array(imagedata.data.buffer);
      stars.length = 0; // o'lcham o'zgarsa yulduzlar qaytadan tug'iladi
    };

    const rotate = (cx: number, cy: number, x: number, y: number, rad: number) => {
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);
      return {
        x: cos * (x - cx) + sin * (y - cy) + cx,
        y: cos * (y - cy) - sin * (x - cx) + cy,
      };
    };

    const createStar = () => {
      // Ikkita tasodifiy sonning o'rtachasi — yulduzlar chekkaga emas,
      // ma'lum bir halqa atrofiga to'planadi (aylana ko'rinishi shundan).
      const orbital =
        (Math.random() * (starEscapeWidth / 2) +
          1 +
          (Math.random() * (starEscapeWidth / 2) + starEscapeWidth)) /
        2;
      const opacity = Math.floor(
        (1 - orbital / starEscapeWidth) * maxOpacity + Math.random() * 80,
      );
      const rotation = Math.PI * (Math.random() * 2);
      const position = rotate(
        size.x / 2, size.y / 2, size.x / 2, size.y / 2 + orbital, rotation,
      );
      stars.push({
        orbital,
        opacity,
        position,
        realPosition: { ...position },
        rotation,
        rSpeed: Math.random() * rotationSpeed + opacity / 20000,
        waveSpeed1: Math.random() * waveSpeed,
        waveSpeed2: Math.random() * waveSpeed,
        wave1: 0,
        wave2: 0,
      });
    };

    const drawStar = (star: Star) => {
      if (!data) return;
      // Avvalgi pikselni o'chiramiz (alfa = 0 -> shaffof)
      const prev =
        Math.floor(star.realPosition.y + star.wave1) * size.x +
        Math.floor(star.realPosition.x + star.wave2);
      if (prev >= 0 && prev < data.length) data[prev] = 0;

      star.wave1 = Math.sin(currentTime * star.waveSpeed1) * waveFrequency;
      star.wave2 = Math.sin(currentTime * star.waveSpeed2) * waveFrequency;
      star.realPosition = rotate(
        size.x / 2, size.y / 2,
        star.position.x, star.position.y,
        star.rSpeed * currentTime,
      );
      star.opacity = Math.floor(
        (1 - star.orbital / starEscapeWidth) * maxOpacity + Math.random() * 80,
      );

      const index =
        Math.floor(star.realPosition.y + star.wave1) * size.x +
        Math.floor(star.realPosition.x + star.wave2);
      if (index >= 0 && index < data.length) {
        // ABGR tartibida (little-endian) qadoqlanadi
        data[index] =
          (Math.min(255, Math.max(0, star.opacity)) << 24) |
          (color.b << 16) |
          (color.g << 8) |
          color.r;
      }
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
    const onVisibility = () => {
      cancelAnimationFrame(frame);
      if (!document.hidden) frame = requestAnimationFrame(render);
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [
    starCount, waveFrequency, starEscapeWidth,
    maxOpacity, rotationSpeed, waveSpeed, isDark,
  ]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
