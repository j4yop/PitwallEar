import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/demo": "http://localhost:8000",
      "/timeline": "http://localhost:8000",
      "/analyse-text": "http://localhost:8000",
      "/analyse": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/live": "http://localhost:8000",
      "/aggregation": "http://localhost:8000",
    },
  },
});
