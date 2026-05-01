import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    files: ["src/features/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          // Запрет hardcoded hex в JSX / style values. Allowed: `var(--*)`
          // semantic токены или brand vars (см. globals.css + ADR-0011).
          selector: "Literal[value=/^#[0-9A-Fa-f]{3,8}$/]",
          message:
            "Hardcoded hex запрещён в features/components. Используй var(--*) из globals.css или brand токены (ADR-0011).",
        },
        {
          selector: "TemplateElement[value.raw=/#[0-9A-Fa-f]{6}/]",
          message:
            "Hardcoded hex в template literal запрещён. Используй var(--*).",
        },
        {
          selector: "Literal[value=/^rgba?\\(/]",
          message:
            "Hardcoded rgb/rgba запрещён. Используй var(--*) или brand токены.",
        },
      ],
    },
  },
]);

export default eslintConfig;
