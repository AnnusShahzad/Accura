#!/usr/bin/env node
// Create backend/.venv (if missing) and install the Python requirements,
// including the test dependencies
// into it, so `npm run dev:backend` always has an interpreter to use.
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const backendDir = path.join(__dirname, "..", "backend");
const isWin = process.platform === "win32";
const venvDir = path.join(backendDir, ".venv");
const venvPython = path.join(venvDir, isWin ? "Scripts" : "bin", isWin ? "python.exe" : "python");

if (!fs.existsSync(venvPython)) {
  const sysPython = isWin ? "python" : "python3";
  console.log(`Creating virtualenv in ${venvDir}`);
  execFileSync(sysPython, ["-m", "venv", venvDir], { stdio: "inherit" });
}
execFileSync(venvPython, ["-m", "pip", "install", "--upgrade", "pip"], { stdio: "inherit" });
// requirements-dev.txt = runtime requirements + the test tooling
execFileSync(venvPython, ["-m", "pip", "install", "-r", path.join(backendDir, "requirements-dev.txt")], {
  stdio: "inherit",
});
