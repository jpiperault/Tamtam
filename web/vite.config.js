import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En développement, l'API tourne à part : TAMTAM_API=http://127.0.0.1:8092 npm run dev
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", proxy: { "/api": process.env.TAMTAM_API || "http://127.0.0.1:8092", "/m": process.env.TAMTAM_API || "http://127.0.0.1:8092" } },
  build: { outDir: "dist", assetsInlineLimit: 0 },
});
