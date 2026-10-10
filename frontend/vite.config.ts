import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  // Reads .env, .env.local etc.; a shell variable of the same name takes precedence.
  const env = { ...loadEnv(mode, process.cwd(), ""), ...process.env };

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": path.resolve(import.meta.dirname, "src") },
    },
    server: {
      host: true,
      port: 5173,
      proxy: {
        "/api": env.API_PROXY_TARGET ?? "http://localhost:8000",
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      globals: true,
      exclude: ["node_modules", "e2e"],
    },
  };
});
