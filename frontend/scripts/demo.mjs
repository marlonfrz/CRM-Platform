import { spawn } from "node:child_process";
import { cpSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const command = process.argv[2];
if (!["dev", "build", "start"].includes(command)) {
  process.exitCode = 1;
} else {
  if (command === "start") {
    const staticSource = fileURLToPath(new URL("../.next/static", import.meta.url));
    const staticTarget = fileURLToPath(new URL("../.next/standalone/.next/static", import.meta.url));
    cpSync(staticSource, staticTarget, { recursive: true });
    const publicSource = fileURLToPath(new URL("../public", import.meta.url));
    const publicTarget = fileURLToPath(new URL("../.next/standalone/public", import.meta.url));
    if (existsSync(publicSource)) cpSync(publicSource, publicTarget, { recursive: true });
  }
  const next = fileURLToPath(new URL(command === "start" ? "../.next/standalone/server.js" : "../node_modules/next/dist/bin/next", import.meta.url));
  const args = command === "start" ? [next] : [next, command];
  if (command === "dev") args.push("--hostname", "127.0.0.1", "--port", "4173");
  const processHandle = spawn(process.execPath, args, {
    stdio: "inherit",
    env: { ...process.env, DEMO_MODE: "true", ...(command === "start" ? { HOSTNAME: "127.0.0.1", PORT: "4173" } : {}) },
  });
  processHandle.on("exit", (code) => { process.exitCode = code ?? 1; });
}
