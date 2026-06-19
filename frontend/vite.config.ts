import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite sozlamasi. server.host=true -> Docker konteyneridan tashqariga ochiq.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,        // 0.0.0.0 — konteyner tashqarisidan localhost:5173 ishlaydi
    port: 5173,
    watch: { usePolling: true },   // Docker volume'da fayl o'zgarishini sezish uchun
  },
});
