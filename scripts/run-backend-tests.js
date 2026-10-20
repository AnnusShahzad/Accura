#!/usr/bin/env node
// Run the backend pytest suite with the project's virtualenv.
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const backendDir = path.join(__dirname, "..", "backend");
const isWin = process.platform === "win32";
const candidates = [".venv", "venv"].map((dir) =>
  path.join(backendDir, dir, isWin ? "Scripts" : "bin", isWin ? "python.exe" : "python")
);
const python =
  candidates.find((p) => fs.existsSync(p)) || (isWin ? "python" : "python3");

const res = spawnSync(python, ["-m", "pytest", "tests", ...process.argv.slice(2)], {
  cwd: backendDir,
  stdio: "inherit",
});
process.exit(res.status ?? 1);
