import { useEffect, useRef, useState } from "react";
import { useTheme } from "../../contexts/ThemeContext";
import html from "./apiDocs.html?raw";

// Admin panel ichidagi API hujjatlari sahifasi.
// Butun hujjat (HTML + CSS + JS) apiDocs.html faylida yashaydi va bu yerga Vite `?raw`
// orqali matn sifatida import qilinadi, so'ng iframe (srcDoc) ichida ko'rsatiladi —
// uslublar admin panelga aralashmaydi (izolyatsiya). Fayl bundle ichida bo'lgani uchun
// alohida ochiq URL yaratilmaydi — faqat shu himoyalangan admin sahifasida ochiladi.
//
// Iframe qattiq balandlikda ("fixed box") bo'lmasligi uchun: hujjat o'z balandligini
// postMessage orqali yuboradi, biz iframe balandligini shunga moslaymiz. Natijada ichki
// skroll yo'q — butun admin sahifasi tabiiy skroll qiladi.
export default function ApiDocsView() {
  const ref = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(900);
  const { theme } = useTheme();

  useEffect(() => {
    function onMsg(e: MessageEvent) {
      const d = e.data;
      if (d && d.type === "apiDocsHeight" && typeof d.height === "number") {
        setHeight(d.height);
      }
    }
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // Admin panel mavzusini (light/dark) hujjatga uzatamiz — u ham mos rangda ko'rinadi.
  const sendTheme = () => {
    ref.current?.contentWindow?.postMessage({ type: "setTheme", theme }, "*");
  };
  useEffect(sendTheme, [theme]);

  return (
    <iframe
      ref={ref}
      title="Turon-AI API hujjatlari"
      srcDoc={html}
      onLoad={sendTheme}
      style={{
        width: "100%",
        height,
        border: "none",
        display: "block",
        background: "transparent",
      }}
    />
  );
}
