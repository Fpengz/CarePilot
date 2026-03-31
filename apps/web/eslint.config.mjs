import { defineConfig } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig([{
    extends: [...nextCoreWebVitals],
}, {
    files: ["**/*.{js,jsx,ts,tsx}"],
    ignores: ["lib/api.ts", "lib/api/*.ts"],

    rules: {
        "no-restricted-imports": ["error", {
            paths: [{
                name: "@/lib/api",
                message: "Use domain clients under @/lib/api/* instead of the legacy consolidated client.",
            }],
        }],
    },
}]);