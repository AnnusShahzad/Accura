// Shared helpers: a page that records console errors, uncaught exceptions
// and failed API calls, plus a step runner that keeps going on failure.
import fs from "fs";

export function makeRunner(page, outDir) {
  fs.mkdirSync(outDir, { recursive: true });
  const problems = [];
  const state = { current: "", expect4xx: false };

  page.on("console", (m) => {
    if (m.type() === "error" && !state.expect4xx) problems.push(`[console] ${state.current}: ${m.text().slice(0, 250)}`);
  });
  page.on("pageerror", (e) => problems.push(`[pageerror] ${state.current}: ${e.message.slice(0, 250)}`));
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/") && r.status() >= 400 && !state.expect4xx) {
      problems.push(`[http ${r.status()}] ${state.current}: ${r.request().method()} ${new URL(r.url()).pathname}`);
    }
  });

  return {
    problems,
    state,
    async visit(base, path, name, waitFor) {
      state.current = path;
      await page.goto(base + path, { waitUntil: "networkidle" });
      if (waitFor) await page.waitForSelector(waitFor);
      await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
    },
    async step(name, fn) {
      try {
        await fn();
        console.log(`  ok   ${name}`);
      } catch (e) {
        problems.push(`[step] ${name}: ${e.message.split("\n").slice(0, 6).join(" | ")}`);
        console.log(`  FAIL ${name}`);
        await page.screenshot({ path: `${outDir}/fail-${name.replace(/\W+/g, "_")}.png`, fullPage: true }).catch(() => {});
      } finally {
        state.expect4xx = false;
      }
    },
    finish() {
      console.log(`\n${problems.length} problem(s)`);
      for (const p of problems) console.log(" - " + p);
      return problems.length ? 1 : 0;
    },
  };
}
