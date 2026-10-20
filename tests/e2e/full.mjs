// Full browser pass over every page and the core flows of a self-hosted
// Accura (registration open). See README.md for how to start the stack.
//
//   BASE=http://localhost:3000 ADMIN_EMAIL=... ADMIN_PASSWORD=... node full.mjs
import { chromium } from "playwright";
import { makeRunner } from "./lib.mjs";

const BASE = process.env.BASE || "http://localhost:3000";
// The API as the browser sees it: the frontend's own /api/v1 in proxy mode,
// or the NEXT_PUBLIC_API_URL the frontend was built with
const API = process.env.API || "/api/v1";
const EMAIL = process.env.ADMIN_EMAIL || "admin@accura.dev";
const PASSWORD = process.env.ADMIN_PASSWORD || "Adm1n!Pass";

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1366, height: 900 } })).newPage();
page.setDefaultTimeout(15000);
const r = makeRunner(page, new URL("./out/full", import.meta.url).pathname);
const visit = (path, name, waitFor) => r.visit(BASE, path, name, waitFor);

// ── Public pages ──
await r.step("landing", () => visit("/", "landing", "text=Simple, Transparent Pricing"));
await r.step("register page", () => visit("/register", "register", "form"));
await r.step("forgot password", () => visit("/forgot-password", "forgot", "form"));
await r.step("reset without token", () => visit("/reset-password", "reset", "text=missing its token"));

await r.step("contact form", async () => {
  await visit("/", "landing-contact", "#contact form");
  const form = page.locator("#contact form");
  await form.locator('input[name="name"]').fill("E2E Visitor");
  await form.locator('input[name="email"]').fill("visitor@example.com");
  await form.locator('textarea[name="message"]').fill("Hello from the e2e test");
  await form.locator('button[type="submit"]').click();
  await page.waitForSelector("text=/message|sent|thank/i");
});

// ── Login: a wrong password must show an error, not bounce ──
await r.step("login wrong password", async () => {
  await visit("/login", "login", "form");
  r.state.expect4xx = true;
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', "Wrong!Pass1");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Invalid email or password");
});

await r.step("login", async () => {
  if (!page.url().endsWith("/login")) await visit("/login", "login", "form");
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/chat");
});

// ── Every dashboard page ──
for (const path of ["/chat", "/chat/new", "/settings", "/settings/profile", "/settings/api-keys",
  "/settings/mcp-servers", "/settings/billing", "/settings/notifications", "/notifications",
  "/admin", "/admin/users", "/admin/plans", "/admin/prompts", "/admin/domains",
  "/admin/mcp-servers", "/admin/config", "/admin/contacts"]) {
  await r.step(`page ${path}`, () => visit(path, path.slice(1).replace(/\//g, "-"), "main h1"));
}

// ── Chat flow ──
await r.step("chat: create, follow up, add agent", async () => {
  await visit("/chat/new", "chat-new-2", "textarea");
  await page.fill("textarea", "Explain photosynthesis briefly");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/chat\/[0-9a-f-]{36}$/);
  r.state.current = page.url();
  await page.waitForSelector("text=Plants turn light into chemical energy", { timeout: 30000 });
  await page.waitForSelector("h1:has-text('Photosynthesis Explained')");

  await page.fill('textarea[placeholder^="Send a follow-up"]', "And in one sentence?");
  await page.keyboard.press("Enter");
  await page.waitForSelector("text=context messages: 3", { timeout: 30000 });
  await page.waitForSelector("text=Processing", { state: "detached", timeout: 30000 });

  await page.locator('button:has-text("Agent")').first().click();
  await page.click('[role="dialog"] button[role="combobox"]');
  await page.click('[role="option"]:has-text("GPT-4o")');
  await page.click('[role="dialog"] button:has-text("Add Agent")');
  await page.waitForSelector("text=Alternative", { timeout: 30000 });

  await page.click('button:has-text("Show Details")');
  await page.waitForSelector("text=/Turn 2 · Iteration #1/");
  await page.screenshot({ path: new URL("./out/full/chat-agent.png", import.meta.url).pathname, fullPage: true });
});

await r.step("chat: failure shows error + retry", async () => {
  // Providers without a key can't be picked any more, so create such a
  // chat through the API to exercise the failure UI.
  await visit("/chat", "chat-list-pre", "main h1");
  const id = await page.evaluate(async (api) => {
    const res = await fetch(api + "/chat", {
      method: "POST",
      headers: { Authorization: "Bearer " + localStorage.getItem("access_token"), "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "This will fail", generator_provider: "deepseek", generator_model: "deepseek-chat" }),
    });
    return (await res.json()).data.id;
  }, API);
  await visit(`/chat/${id}`, "chat-failed");
  await page.waitForSelector("text=The response could not be generated", { timeout: 30000 });
  await page.waitForSelector('button:has-text("Retry")');
  await visit("/chat", "chat-list-2", "text=Failed");
});

// ── Settings flows ──
await r.step("settings save", async () => {
  await visit("/settings", "settings-2", "form");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Settings saved");
});

await r.step("api key: custom provider needs a URL", async () => {
  await visit("/settings/api-keys", "api-keys-2", "main h1");
  await page.locator("main button", { hasText: /Add/ }).first().click();
  await page.click('[role="dialog"] button[role="combobox"]');
  await page.click('[role="option"]:has-text("Custom")');
  await page.fill('[role="dialog"] input[type="password"]', "sk-custom-123456789");
  await page.click('[role="dialog"] button[type="submit"]');
  await page.waitForSelector("text=A base URL is required for custom providers");
  await page.fill('[role="dialog"] input[placeholder^="https://your-endpoint"]', "http://127.0.0.1:8099/v1");
  await page.click('[role="dialog"] button[type="submit"]');
  await page.waitForSelector("text=sk-c...6789");
});

await r.step("billing: upgrade, MCP unlocked, downgrade", async () => {
  await visit("/settings/billing", "billing-2", "text=Subscription Plans");
  await page.click('button:has-text("Upgrade")');
  await page.waitForSelector("text=Demo mode");
  await page.fill("#card", "4242 4242 4242 4242");
  await page.fill("#expiry", "12/30");
  await page.fill("#cvc", "123");
  await page.click('button:has-text("Activate Plan")');
  await page.waitForSelector("button:has-text('Cancel Plan')");

  await visit("/settings/mcp-servers", "mcp-pro", "main h1");
  if (await page.locator('button:has-text("Add Server")').isDisabled()) {
    throw new Error("Add Server still disabled for a Pro user");
  }

  await visit("/settings/billing", "billing-3", "button:has-text('Cancel Plan')");
  await page.click('button:has-text("Cancel Plan")');
  await page.click('[role="dialog"] button:has-text("Cancel plan")');
  await page.waitForSelector("text=Subscription cancelled");
});

await r.step("admin config: add and delete an override", async () => {
  await visit("/admin/config", "config-2", "main h1");
  await page.locator('button:has-text("Add Override")').first().click();
  await page.fill("#config-key", "evaluation.global_threshold");
  await page.fill("#config-value", "80");
  await page.click('[role="dialog"] button:has-text("Save")');
  await page.waitForSelector("td:has-text('evaluation.global_threshold')");
  await page.click('button[aria-label="Delete evaluation.global_threshold"]');
  await page.click('[role="alertdialog"] button:has-text("Remove")');
  await page.waitForSelector("text=No Overrides");
});

await r.step("notifications list", () => visit("/notifications", "notifications-2", "text=Response Ready"));

await r.step("logout", async () => {
  await page.click('button:has-text("Logout")');
  await page.waitForURL("**/login");
});

await browser.close();
process.exit(r.finish());
