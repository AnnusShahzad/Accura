# Accura Frontend

Next.js 16 (App Router) + React 19 client for the Accura API. UI is built
from shadcn/ui components, server state lives in TanStack Query and the
signed-in user in a small Zustand store.

## Setup

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, default http://localhost:8000/api/v1
npm install                  # or `npm install` at the repository root
npm run dev                  # http://localhost:3000
```

The backend must be running (see the repository README); `npm run dev` at
the repository root starts both.

## Scripts

| Script | Description |
|:--|:--|
| `npm run dev` | Development server |
| `npm run build` | Production build (`NEXT_PUBLIC_API_URL` is inlined at build time) |
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
