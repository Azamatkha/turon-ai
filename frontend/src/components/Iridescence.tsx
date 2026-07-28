import { Renderer, Program, Mesh, Color, Triangle } from "ogl";
import { useEffect, useRef } from "react";

import "./Iridescence.css";

// Jonli, oqib turuvchi rangli fon (WebGL shader). Chat sahifasida gradient +
// DotField o'rniga ishlatiladi — light rejimda ham aniq ko'rinadi.

const vertexShader = `
attribute vec2 uv;
attribute vec2 position;

varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position, 0, 1);
}
`;

const fragmentShader = `
precision highp float;

uniform float uTime;
uniform vec3 uColor;
uniform vec3 uColorB;
uniform vec3 uResolution;
uniform vec2 uMouse;
uniform float uAmplitude;
uniform float uSpeed;

varying vec2 vUv;

void main() {
  float mr = min(uResolution.x, uResolution.y);
  vec2 uv = (vUv.xy * 2.0 - 1.0) * uResolution.xy / mr;

  uv += (uMouse - vec2(0.5)) * uAmplitude;

  float d = -uTime * 0.5 * uSpeed;
  float a = 0.0;
  for (float i = 0.0; i < 8.0; ++i) {
    a += cos(i - d - a * uv.x);
    d += sin(uv.y * i + a);
  }
  d += uTime * 0.5 * uSpeed;
  vec3 col = vec3(cos(uv * vec2(d, a)) * 0.6 + 0.4, cos(a + d) * 0.5 + 0.5);
  col = cos(col * cos(vec3(d, a, 2.5)) * 0.5 + 0.5);

  // MUHIM: asl shader kamalak (RGB) ranglar chiqaradi — uColor bilan
  // ko'paytirish binafsha/pushti tovlanishni yo'qotmaydi. Shuning uchun
  // naqshni avval BITTA skalyar qiymatga aylantiramiz, so'ng uni faqat
  // ikki brend rangi (uColor -> uColorB) orasida aralashtiramiz. Natijada
  // rang doirasi qat'iy nazoratda: begona hue umuman paydo bo'lmaydi.
  // Naqshning o'rtacha qiymati tor diapazonda tebranadi — shuning uchun uni
  // markaz atrofida CHO'ZAMIZ, aks holda rang deyarli o'zgarmas bo'lib qoladi.
  float t = dot(col, vec3(0.3333));
  t = clamp((t - 0.38) * 3.2 + 0.5, 0.0, 1.0);
  // Uch bosqichli ramp: quyuq -> o'rta -> yorug'. Bir xil hue oilasida qoladi,
  // lekin oqim aniq ko'rinadi.
  vec3 mid = mix(uColor, uColorB, 0.5) * 1.06;
  vec3 outc = t < 0.5
    ? mix(uColor, mid, t * 2.0)
    : mix(mid, uColorB, (t - 0.5) * 2.0);
  gl_FragColor = vec4(outc, 1.0);
}
`;

interface IridescenceProps {
  /** Naqshning quyuq (past) tomoni — odatda to'q navy */
  color?: [number, number, number];
  /** Naqshning yorug' (baland) tomoni — odatda ochiq havorang */
  colorB?: [number, number, number];
  speed?: number;
  amplitude?: number;
  mouseReact?: boolean;
}

export default function Iridescence({
  color = [0.1, 0.24, 0.46],
  colorB = [0.55, 0.72, 0.9],
  speed = 1.0,
  amplitude = 0.1,
  mouseReact = true,
  ...rest
}: IridescenceProps) {
  const ctnDom = useRef<HTMLDivElement>(null);
  const mousePos = useRef({ x: 0.5, y: 0.5 });

  useEffect(() => {
    if (!ctnDom.current) return;
    const ctn = ctnDom.current;
    const renderer = new Renderer();
    const gl = renderer.gl;
    gl.clearColor(1, 1, 1, 1);

    let program: Program;

    function resize() {
      const scale = 1;
      renderer.setSize(ctn.offsetWidth * scale, ctn.offsetHeight * scale);
      if (program) {
        program.uniforms.uResolution.value = new Color(
          gl.canvas.width,
          gl.canvas.height,
          gl.canvas.width / gl.canvas.height
        );
      }
    }
    window.addEventListener("resize", resize, false);
    resize();

    const geometry = new Triangle(gl);
    program = new Program(gl, {
      vertex: vertexShader,
      fragment: fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new Color(...color) },
        uColorB: { value: new Color(...colorB) },
        uResolution: {
          value: new Color(
            gl.canvas.width,
            gl.canvas.height,
            gl.canvas.width / gl.canvas.height
          ),
        },
        uMouse: {
          value: new Float32Array([mousePos.current.x, mousePos.current.y]),
        },
        uAmplitude: { value: amplitude },
        uSpeed: { value: speed },
      },
    });

    const mesh = new Mesh(gl, { geometry, program });
    let animateId: number;

    function update(t: number) {
      animateId = requestAnimationFrame(update);
      program.uniforms.uTime.value = t * 0.001;
      renderer.render({ scene: mesh });
    }
    animateId = requestAnimationFrame(update);
    ctn.appendChild(gl.canvas);

    function handleMouseMove(e: MouseEvent) {
      const rect = ctn.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1.0 - (e.clientY - rect.top) / rect.height;
      mousePos.current = { x, y };
      program.uniforms.uMouse.value[0] = x;
      program.uniforms.uMouse.value[1] = y;
    }
    if (mouseReact) {
      ctn.addEventListener("mousemove", handleMouseMove);
    }

    return () => {
      cancelAnimationFrame(animateId);
      window.removeEventListener("resize", resize);
      if (mouseReact) {
        ctn.removeEventListener("mousemove", handleMouseMove);
      }
      ctn.removeChild(gl.canvas);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, [color, colorB, speed, amplitude, mouseReact]);

  return <div ref={ctnDom} className="iridescence-container" {...rest} />;
}
