# Browser end-to-end checks

Playwright suites used to verify Accura in a real browser. They live
outside the app workspaces, so deployments never install them.

```bash
cd tests/e2e
npm install && npx playwright install chromium
python3 fake_openai.py &          # OpenAI-compatible stub on :8099
```

| Suite | Checks | Typical target |
|:--|:--|:--|
| `full.mjs` | Every page and the core flows (chat, follow-ups, agents, retry, settings, keys, billing, admin) | Self-hosted, registration open |
| `demo.mjs` | The public-demo setup from `DEPLOYMENT.md`: closed registration, guests, guest limits, SSRF guard, bootstrap admin | The single container |
| `audit.mjs` | axe-core (WCAG 2 A/AA) plus overflow, clipping and tap-target checks on every page, desktop and phone, light and dark | Either |

All suites print a list of problems (console errors, uncaught exceptions,
failed API calls, failed steps) and exit non-zero if there are any.
Screenshots go to `out/`.

## Against the single container (public demo)

```bash
docker build -t accura ../..
docker run --network host -e PORT=10500 -e DATABASE_URL=postgres://... \
  -e JWT_SECRET=... -e ENCRYPTION_KEY=... \
  -e REGISTRATION_ENABLED=false -e GUEST_ENABLED=true -e ALLOW_PRIVATE_URLS=false \
  -e ADMIN_EMAIL=owner@example.com -e ADMIN_PASSWORD='Own3r!Pass' \
  -e DEFAULT_AI_PROVIDER=custom -e CUSTOM_AI_API_KEY=sk-fake \
  -e CUSTOM_AI_BASE_URL=http://127.0.0.1:8099/v1 \
  -e DEFAULT_GENERATOR_MODEL=openai/gpt-oss-20b:free \
  -e DEFAULT_EVALUATOR_MODEL=openai/gpt-oss-20b:free accura

BASE=http://localhost:10500 DEFAULT_MODEL=openai/gpt-oss-20b:free node demo.mjs
BASE=http://localhost:10500 node audit.mjs   # needs the admin to have a chat
```

## Against a local development stack

Start the backend with `OPENAI_API_KEY=sk-fake OPENAI_BASE_URL=http://127.0.0.1:8099/v1`
and an admin (`ADMIN_EMAIL`/`ADMIN_PASSWORD`), and the frontend with
`npm run dev`, then:

```bash
BASE=http://localhost:3000 ADMIN_EMAIL=... ADMIN_PASSWORD=... node full.mjs
```
