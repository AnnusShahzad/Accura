// UI audit: every page × {desktop, phone} × {light, dark}.
// axe-core (WCAG 2 A/AA: contrast, names, labels) plus layout checks for
// horizontal overflow, content wider than the viewport, clipped text and
// tap targets under 24px on phones. Screenshots land in out/audit/ for a
// visual pass. Needs an account with at least one finished chat.
//
//   BASE=http://localhost:3100 API=http://localhost:10000/api/v1 \
//   ADMIN_EMAIL=... ADMIN_PASSWORD=... node audit.mjs
import { chromium } from "playwright";
import fs from "fs";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const AXE = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const BASE = process.env.BASE || "http://localhost:3100";
const API = process.env.API || "/api/v1";
const EMAIL = process.env.ADMIN_EMAIL || "owner@example.com";
const PASSWORD = process.env.ADMIN_PASSWORD || "Own3r!Pass";
const OUT = new URL("./out/audit/", import.meta.url).pathname;
fs.mkdirSync(OUT, { recursive: true });

const PUBLIC = ["/", "/login", "/register", "/forgot-password", "/reset-password"];
const PRIVATE = ["/chat", "/chat/new", "CHAT", "/settings", "/settings/profile", "/settings/api-keys",
  "/settings/mcp-servers", "/settings/billing", "/settings/notifications", "/notifications",
  "/admin", "/admin/users", "/admin/plans", "/admin/prompts", "/admin/domains", "/admin/mcp-servers",
  "/admin/config", "/admin/contacts"];

const findings = new Map();
function note(key, variant) {
  const f = findings.get(key) || new Set();
  f.add(variant);
  findings.set(key, f);
}

function layoutChecks(page, mobile) {
  return page.evaluate((mobile) => {
    const out = [];
    const vw = window.innerWidth;
    const doc = document.documentElement;
    if (doc.scrollWidth > vw + 1) out.push(`page scrolls horizontally (+${doc.scrollWidth - vw}px)`);
    const describe = (el) => {
      const cls = (el.getAttribute("class") || "").split(" ").slice(0, 3).join(".");
      const txt = (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 30).replace(/\s+/g, " ");
      return `<${el.tagName.toLowerCase()}${cls ? "." + cls : ""}> "${txt}"`;
    };
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || el.classList.contains("sr-only")) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (el.closest("[data-radix-scroll-area-viewport], pre, code, table, [data-slot=sidebar], .katex-display")) continue;
      if (r.right > vw + 2 && cs.position !== "fixed") out.push(`wider than viewport: ${describe(el)}`);
      if (el.children.length === 0 && el.innerText && el.innerText.trim().length > 2 &&
          el.scrollWidth > el.clientWidth + 2 && cs.overflow !== "visible" &&
          cs.textOverflow !== "ellipsis" && !["INPUT", "TEXTAREA"].includes(el.tagName)) {
        out.push(`clipped text: ${describe(el)}`);
      }
      if (mobile && el.matches("button, a[href], [role=button], [role=combobox], [role=switch]") &&
          !el.closest("p, li")) {
        // An absolutely positioned ::after enlarges the hit area: switches
        // extend past their edges, stretched links cover their whole card.
        // Measure the ::after box rather than the element's own rect.
        const after = getComputedStyle(el, "::after");
        let hit = r;
        if (after.content !== "none" && after.position === "absolute") {
          // ::after is placed against the element itself if it's positioned,
          // otherwise against its nearest positioned ancestor
          const host = cs.position !== "static" ? el : el.offsetParent || el;
          const hr = host.getBoundingClientRect();
          const px = (v) => (v === "auto" ? null : parseFloat(v));
          const [t, rt, b, l] = [px(after.top), px(after.right), px(after.bottom), px(after.left)];
          if ([t, rt, b, l].every((v) => v !== null)) {
            // The hit area is whichever box is larger (a decorative
            // underline ::after doesn't shrink the button)
            hit = {
              width: Math.max(r.width, hr.width - l - rt),
              height: Math.max(r.height, hr.height - t - b),
            };
          }
        }
        if (hit.width < 24 || hit.height < 24) {
          out.push(`small tap target ${Math.round(r.width)}x${Math.round(r.height)}: ${describe(el)}`);
        }
      }
    }
    return [...new Set(out)];
  }, mobile);
}

const browser = await chromium.launch();

async function firstChatId(page) {
  return page.evaluate(async (API) => {
    const h = { Authorization: "Bearer " + localStorage.getItem("access_token") };
    const list = await (await fetch(API + "/chat?per_page=1", { headers: h })).json();
    return list.data.items[0]?.id ?? null;
  }, API);
}

for (const mobile of [false, true]) {
  for (const dark of [false, true]) {
    const variant = `${mobile ? "phone" : "desktop"}-${dark ? "dark" : "light"}`;
    const ctx = await browser.newContext({
      viewport: mobile ? { width: 390, height: 844 } : { width: 1366, height: 900 },
      isMobile: mobile, hasTouch: mobile, colorScheme: dark ? "dark" : "light",
    });
    await ctx.addInitScript((t) => localStorage.setItem("theme", t), dark ? "dark" : "light");
    const page = await ctx.newPage();
    page.setDefaultTimeout(15000);
    let chatId = null;
    for (const group of [PUBLIC, PRIVATE]) {
      if (group === PRIVATE) {
        await page.goto(BASE + "/login", { waitUntil: "networkidle" });
        await page.fill('input[type="email"]', EMAIL);
        await page.fill('input[type="password"]', PASSWORD);
        await page.click('button[type="submit"]');
        await page.waitForURL("**/chat");
        chatId = await firstChatId(page);
      }
      for (const raw of group) {
        if (raw === "CHAT" && !chatId) continue;
        const path = raw === "CHAT" ? `/chat/${chatId}` : raw;
        const name = raw === "CHAT" ? "chat-detail" : path.replace(/\//g, "-").replace(/^-/, "") || "landing";
        await page.goto(BASE + path, { waitUntil: "networkidle" });
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${OUT}${variant}__${name}.png`, fullPage: true });
        await page.addScriptTag({ content: AXE });
        const violations = await page.evaluate(async () => {
          const res = await window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa"] });
          return res.violations.map((v) => ({
            id: v.id,
            nodes: v.nodes.slice(0, 4).map((n) => n.target.join(" ") + " :: " + (n.any[0]?.message || "").slice(0, 90)),
          }));
        });
        for (const v of violations) for (const n of v.nodes) note(`[axe:${v.id}] ${name}: ${n}`, variant);
        for (const issue of await layoutChecks(page, mobile)) note(`[layout] ${name}: ${issue}`, variant);
      }
    }
    await ctx.close();
  }
}
await browser.close();

const rows = [...findings.entries()].map(([k, v]) => `${[...v].join(",").padEnd(46)} ${k}`).sort();
fs.writeFileSync(OUT + "findings.txt", rows.join("\n") + "\n");
console.log(rows.length ? rows.join("\n") : "no findings");
console.log(`\n${rows.length} finding(s); screenshots in ${OUT}`);
process.exit(rows.length ? 1 : 0);
