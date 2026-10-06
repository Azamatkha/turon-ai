import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Vite sozlamasi. server.host=true -> Docker konteyneridan tashqariga ochiq.
export default defineConfig(({ mode }) => {
  // Ilova domen ildizida emas, ichki yo'lda (masalan /chat/) tursa, VITE_BASE_PATH
  // beriladi: asset manzillari va router basename (main.tsx) shundan olinadi.
  // Lokal `npm run dev` da berilmaydi -> "/".
  const env = loadEnv(mode, ".", "VITE_");
  return {
    base: env.VITE_BASE_PATH || "/",
    plugins: [react()],
    server: {
      host: true,        // 0.0.0.0 — konteyner tashqarisidan localhost:5173 ishlaydi
      port: 5173,
      watch: { usePolling: true },   // Docker volume'da fayl o'zgarishini sezish uchun
    },
  };
});
