#!/usr/bin/env node
// Start the Sanic backend with the project's virtualenv if one exists,
// falling back to whatever python is on PATH. Works on Linux, macOS and
// Windows so the root npm scripts don't hardcode a platform layout.
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const backendDir = path.join(__dirname, "..", "backend");
const isWin = process.platform === "win32";
const candidates = [".venv", "venv"].map((dir) =>
  path.join(backendDir, dir, isWin ? "Scripts" : "bin", isWin ? "python.exe" : "python")
);
const python =
  candidates.find((p) => fs.existsSync(p)) || (isWin ? "python" : "python3");

const child = spawn(python, ["app.py", ...process.argv.slice(2)], {
  cwd: backendDir,
  stdio: "inherit",
});
child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 0);
});
for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}
