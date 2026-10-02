import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { createClient } from "@hey-api/openapi-ts";

const backend = resolve(import.meta.dirname, "../../backend");
const python = process.env.CRM_PYTHON ?? resolve(
  backend,
  process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
);
const schema = resolve(import.meta.dirname, "../openapi.json");

execFileSync(python, [resolve(backend, "scripts/export_openapi.py"), schema], { stdio: "inherit" });
await createClient({
  input: schema,
  output: resolve(import.meta.dirname, "../src/lib/api-generated"),
  plugins: ["@hey-api/typescript"],
});
