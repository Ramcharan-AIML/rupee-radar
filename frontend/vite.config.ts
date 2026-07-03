import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server runs on :5173 and proxies /api to the FastAPI backend on :8000,
// so the frontend can call the API with same-origin relative URLs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
