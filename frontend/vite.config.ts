/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1200 },
  server: {
    port: 5173,
    proxy: { "/api": backend },
    // The in-app guide imports ../docs/USAGE.md.
    fs: { allow: [".."] },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
