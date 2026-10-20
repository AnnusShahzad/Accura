# Deploying Accura on free tiers

This guide puts Accura online for free as a **public demo**: sign-up is
closed, visitors try it with one-click **guest accounts** that are deleted
after 24 hours, and you keep an admin account.

| Part | Where | Why |
|:--|:--|:--|
| Backend API | **Render** free web service | Answers are generated in background tasks after the request returns. That needs a long-running process, which serverless platforms (including Vercel Functions) don't provide. |
| Database | **Render** free PostgreSQL, or **Neon** free | Free instances have no persistent disk, so SQLite would be wiped on every deploy. |
| Frontend | **Vercel** (recommended) or Render | Standard Next.js app. |

You need: a GitHub account with this repository, a Render account, and an
API key for at least one AI provider (see [AI provider](#ai-provider)).

---

## Option A – everything on Render (one Blueprint)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, select the repository. Render reads
   [`render.yaml`](render.yaml) and proposes `accura-api`, `accura-db` and
   `accura-web`.
3. Fill in the prompted values:

   | Variable | Value |
   |:--|:--|
   | `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Your admin login. The password needs 9+ characters with upper, lower, number and symbol. |
   | `OPENAI_API_KEY` | Your key, or leave empty and configure another provider (below). |
   | `APP_FRONTEND_URL` | `https://accura-web.onrender.com` (the web service's URL) |
   | `NEXT_PUBLIC_API_URL` | `https://accura-api.onrender.com/api/v1` |

   Render appends a suffix to a service URL if the name is already taken.
   If that happens, correct the two URLs above in the service's
   **Environment** tab and redeploy `accura-web`. Its API URL is compiled
   into the build.
4. **Apply**. The first build takes a few minutes. Then open the web
   service's URL.

## Option B – API on Render, frontend on Vercel

1. Do Option A, but delete `accura-web` from the Blueprint before
   applying, or suspend it afterwards. Note the API URL, e.g.
   `https://accura-api.onrender.com`.
2. In Vercel: **Add New → Project**, import the repository and set:
   - **Root Directory**: `frontend`. The included `vercel.json` installs
     from the repository root, so leave "Include files outside the root
     directory" enabled (the default).
   - **Environment variable**: `NEXT_PUBLIC_API_URL` =
     `https://accura-api.onrender.com/api/v1`
3. Deploy, then set the API's `APP_FRONTEND_URL` on Render to the Vercel
   URL (used in emailed links).

`NEXT_PUBLIC_API_URL` is read at **build** time, so redeploy the frontend
after changing it.

---

## AI provider

Accura talks to every provider through the OpenAI-compatible API. Set
**one** of these on the API service:

**OpenAI**
```
OPENAI_API_KEY=sk-...
```

**Any OpenAI-compatible endpoint** (OpenRouter, Groq, Together, a
self-hosted vLLM, ...). For example, OpenRouter with a free model:
```
DEFAULT_AI_PROVIDER=custom
CUSTOM_AI_BASE_URL=https://openrouter.ai/api/v1
CUSTOM_AI_API_KEY=sk-or-...
DEFAULT_GENERATOR_MODEL=openai/gpt-oss-20b:free
DEFAULT_EVALUATOR_MODEL=openai/gpt-oss-20b:free
```
Model ids are provider-specific, so check the provider's model list.
Free models are rate-limited and may be slow.

DeepSeek, Anthropic and Google work the same way via `DEEPSEEK_API_KEY`,
`ANTHROPIC_API_KEY` and `GOOGLE_AI_API_KEY`.

The app only offers models for providers that have a key, and new chats
default to `DEFAULT_GENERATOR_MODEL`. Users can also add their own keys
under **Settings → API Keys**.

Guests spend **your** key. Their usage is capped:
`GUEST_REQUESTS_PER_DAY` (30), `GUEST_REQUESTS_PER_MINUTE` (5),
`GUEST_MAX_ITERATIONS` (3), and at most 5 new guest sessions per IP per
hour.

## Database

`render.yaml` creates a free Render PostgreSQL database and passes it in
as `DATABASE_URL`. Render's free databases expire after a limited period
(30 days at the time of writing). For a database that lasts, create a free
project on [Neon](https://neon.tech) and set its connection string as
`DATABASE_URL` (keep `?sslmode=require`), then remove the
`accura-db` database.

Tables are created on first start and new columns are added automatically
on upgrade. No migration step is needed.

---

## What to expect on free tiers

- **Sleeping.** Render's free instances stop after about 15 idle minutes,
  and the next visit waits roughly a minute while the API starts. The app
  shows "Starting the server…" and continues on its own.
- **Restarts.** A deploy or restart interrupts answers that are still
  being generated. Those chats show "The server restarted before this
  response finished" with a **Retry** button.
- **Guests** are deleted, with everything they created, `GUEST_TTL_HOURS`
  after they start. The cleanup job runs every 5 minutes while the server
  is awake, and expired sessions stop working immediately either way.
- **Email** isn't needed for the demo setup, since registration is closed.
  Without SMTP, password-reset emails can't be sent. To reset the admin
  password, change `ADMIN_PASSWORD` and restart.
- **Billing** runs in demo mode (no charges) unless you add Stripe keys.
  Guests can't change plans.

## Settings reference (public demo)

| Variable | Demo value | Meaning |
|:--|:--|:--|
| `REGISTRATION_ENABLED` | `false` | Self-service sign-up |
| `GUEST_ENABLED` | `true` | "Continue as guest" |
| `GUEST_TTL_HOURS` | `24` | Guest lifetime |
| `ALLOW_PRIVATE_URLS` | `false` | Forbid MCP / custom-endpoint / webhook URLs on private networks (SSRF protection). Keep `false` when strangers can sign in. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | yours | Admin created or updated on every start |
| `JWT_SECRET`, `ENCRYPTION_KEY` | generated | Any long random strings. Don't change `ENCRYPTION_KEY` later, or stored API keys can't be decrypted. |
| `APP_CORS_ORIGINS` | `*` | Can be narrowed to your frontend URL |

All other settings are listed in [`backend/.env.example`](backend/.env.example).
Admins can also override most settings at runtime under
**Admin → Configuration**.

## After deploying

1. `https://<api>/api/v1/health` returns `{"status": "healthy", ...}`.
2. `https://<api>/api/v1/public/config` shows `"registration_enabled": false`,
   guests enabled, and your provider under `available_providers`.
3. On the site, **Continue as guest** and send a prompt. You should get a
   scored answer.
4. Log out, sign in with `ADMIN_EMAIL`, and open **Admin**.

## Troubleshooting

| Symptom | Fix |
|:--|:--|
| "Can't reach the server" never clears | Check that `NEXT_PUBLIC_API_URL` ends in `/api/v1` and points at the API's public URL, then redeploy the frontend. |
| Every chat fails with "No API key configured for provider …" | Configure a provider on the API service (see [AI provider](#ai-provider)). With a custom endpoint, also set `DEFAULT_AI_PROVIDER=custom`. |
| Models show "needs API key" | That provider has no key on the server. Add one, or use the defaults. |
| API won't start: "Insecure configuration" | `JWT_SECRET` or `ENCRYPTION_KEY` is missing. Render's Blueprint generates both. Set them by hand on other hosts. |
| Admin can't log in | `ADMIN_PASSWORD` must meet the password policy. Check the API logs for "ADMIN_PASSWORD rejected". |
| Data disappears after a deploy | The API is using SQLite. Make sure `DATABASE_URL` is set. |
