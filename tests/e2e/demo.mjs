// Browser checks for a public-demo deployment (DEPLOYMENT.md): registration
// closed, guest sessions on, SSRF guard on, bootstrap admin.
//
//   BASE=http://localhost:3100 ADMIN_EMAIL=... ADMIN_PASSWORD=... \
//   DEFAULT_MODEL=openai/gpt-oss-20b:free node demo.mjs
import { chromium } from "playwright";
import { makeRunner } from "./lib.mjs";

const BASE = process.env.BASE || "http://localhost:3100";
const EMAIL = process.env.ADMIN_EMAIL || "owner@example.com";
const PASSWORD = process.env.ADMIN_PASSWORD || "Own3r!Pass";
const DEFAULT_MODEL = process.env.DEFAULT_MODEL || "";

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1366, height: 900 } })).newPage();
page.setDefaultTimeout(15000);
page.on("dialog", (d) => d.accept()); // guest logout confirmation
const r = makeRunner(page, new URL("./out/demo", import.meta.url).pathname);
const visit = (path, name, waitFor) => r.visit(BASE, path, name, waitFor);

await r.step("landing offers guest access, not sign-up", async () => {
  await visit("/", "landing", "button:has-text('Try it as a guest')");
  if (await page.locator("text=Get Started Free").count()) throw new Error("sign-up CTA still shown");
});

await r.step("register page says closed", () => visit("/register", "register-closed", "text=Registration is closed"));

await r.step("login page: guest button, no sign-up link", async () => {
  await visit("/login", "login", "button:has-text('Continue as guest')");
  if (await page.locator("a:has-text('Sign up')").count()) throw new Error("Sign up link visible");
});

await r.step("guest session starts", async () => {
  await page.click("button:has-text('Continue as guest')");
  await page.waitForURL("**/chat");
  await page.waitForSelector("text=Guest session.");
});

await r.step("guest chat with the server's default model", async () => {
  await visit("/chat/new", "guest-new-chat", "textarea");
  const trigger = page.locator('button[role="combobox"]').first();
  const label = await trigger.innerText();
  if (DEFAULT_MODEL && !label.includes(DEFAULT_MODEL)) throw new Error(`default model not applied: ${label}`);
  await trigger.click();
  if ((await page.locator('[role="option"][data-disabled]').count()) < 1) {
    throw new Error("models without a key should be disabled");
  }
  await page.keyboard.press("Escape");
  await page.fill("textarea", "Explain photosynthesis briefly");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/chat\/[0-9a-f-]{36}$/);
  r.state.current = page.url();
  await page.waitForSelector("text=Plants turn light into chemical energy", { timeout: 40000 });
  await page.waitForSelector("text=Processing", { state: "detached", timeout: 30000 });
  await page.click('button:has-text("Show Details")');
  const iterations = await page.locator("text=/Turn 1 · Iteration #/").count();
  if (iterations > 3) throw new Error(`guest ran ${iterations} iterations, cap is 3`);
});

await r.step("guest profile hides account security", async () => {
  await visit("/settings/profile", "guest-profile", "text=Guest account");
  if (await page.locator("text=Change Password").count()) throw new Error("password form visible");
});

await r.step("guest billing is read-only", async () => {
  await visit("/settings/billing", "guest-billing", "text=Guest accounts stay on the Basic plan");
  if (!(await page.locator("button:has-text('Upgrade')").first().isDisabled())) throw new Error("Upgrade enabled");
});

await r.step("SSRF guard rejects a private custom endpoint", async () => {
  await visit("/settings/api-keys", "guest-keys", "main h1");
  await page.locator("main button", { hasText: /Add/ }).first().click();
  await page.click('[role="dialog"] button[role="combobox"]');
  await page.click('[role="option"]:has-text("Custom")');
  await page.fill('[role="dialog"] input[type="password"]', "sk-custom-123456789");
  await page.fill('[role="dialog"] input[placeholder^="https://your-endpoint"]', "http://169.254.169.254/v1");
  r.state.expect4xx = true;
  await page.click('[role="dialog"] button[type="submit"]');
  await page.waitForSelector("text=/private or local network/");
  await page.keyboard.press("Escape");
});

await r.step("other pages render for a guest", async () => {
  for (const p of ["/chat", "/settings", "/settings/mcp-servers", "/settings/notifications", "/notifications"]) {
    await visit(p, `guest${p.replace(/\//g, "-")}`, "main h1");
  }
});

await r.step("guest logout", async () => {
  await page.click('button:has-text("Logout")');
  await page.waitForURL("**/login");
});

await r.step("bootstrap admin can sign in and administer", async () => {
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/chat");
  for (const p of ["/admin", "/admin/plans", "/admin/config", "/admin/contacts", "/admin/users"]) {
    await visit(p, `admin${p.replace(/\//g, "-")}`, "main h1");
  }
  // The guests created above are listed and marked as such
  await page.waitForSelector("td >> text=Guest");
});

await browser.close();
process.exit(r.finish());
