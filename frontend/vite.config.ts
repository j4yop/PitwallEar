import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/demo": "http://localhost:8000",
      "/timeline": "http://localhost:8000",
      "/analyse": "http://localhost:8000",
      "/analyse-text": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
