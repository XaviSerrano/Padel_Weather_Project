import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, ".", "VITE_");

  return {
    root: "web",
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: environment.VITE_BACKEND_URL ?? "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "../dist",
      emptyOutDir: true,
    },
  };
});
