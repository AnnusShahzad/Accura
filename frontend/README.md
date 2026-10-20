# Accura Frontend

Next.js 16 (App Router) + React 19 client for the Accura API. UI is built
from shadcn/ui components, server state lives in TanStack Query and the
signed-in user in a small Zustand store.

## Setup

```bash
cp .env.example .env.local   # optional, see below
npm install                  # or `npm install` at the repository root
npm run dev                  # http://localhost:3000
```

The backend must be running (see the repository README); `npm run dev` at
the repository root starts both.

API location (both read at build time):

- `NEXT_PUBLIC_API_URL` – call an API on another host directly, e.g.
  `https://api.example.com/api/v1` (the API's CORS settings must allow it).
- otherwise the app calls its own `/api/v1`, which `next.config.ts`
  proxies to `BACKEND_URL` (default `http://localhost:8000`). The
  production image uses this mode, with the API in the same container.

Deployment is described in [`../DEPLOYMENT.md`](../DEPLOYMENT.md).

## Scripts

| Script | Description |
|:--|:--|
| `npm run dev` | Development server |
| `npm run build` | Production build (`NEXT_PUBLIC_API_URL`/`BACKEND_URL` are read at build time; `NEXT_OUTPUT=standalone` for the container) |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (Next.js + React Compiler rules) |

## Layout

```
src/
├── app/
│   ├── (auth)/        # login, register, OTP, password reset, email change
│   ├── (dashboard)/   # chat, settings, notifications, admin (auth-guarded)
│   └── page.tsx       # public landing page with live pricing and contact form
├── components/        # landing/, layout/, providers/, ui/ (shadcn)
├── hooks/             # use-auth, use-chat, use-settings
├── lib/               # api-client (fetch + token refresh), constants, validations (zod)
├── stores/            # Zustand stores
└── types/             # API response types
```

Tokens are kept in `localStorage`; `lib/api-client.ts` refreshes an expired
access token once (shared between concurrent requests) and sends the user to
`/login` when the refresh token is no longer valid.
