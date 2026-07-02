import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API runs on :8000. Proxy /api and /audio so the app can use relative URLs
// (no CORS, no hardcoded host).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/audio": "http://localhost:8000",
    },
  },
});
