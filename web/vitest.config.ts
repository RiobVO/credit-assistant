import path from "node:path";
import { defineConfig } from "vitest/config";

// CA-040: minimal vitest config. esbuild JSX transform вместо @vitejs/plugin-react —
// fast refresh в тестах не нужен, экономим dep. globals=false: явный импорт
// describe/it/expect из "vitest" в каждом файле (читаемее в IDE, без неявной магии).
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve("./src"),
    },
  },
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: false,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
