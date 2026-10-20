# Accura Backend

Production-grade AI response orchestration platform built with **Sanic** + **Piccolo ORM**.

## Architecture

```
backend/
├── app.py                  # Sanic application entry point
├── config.py               # YAML + env config loader
├── config.yaml             # Default YAML configuration
├── piccolo_conf.py         # Piccolo ORM database config
├── piccolo_app.py          # Piccolo app definition
│
├── models/                 # Piccolo ORM table definitions
│   ├── user.py             # User & UserProfile
│   ├── subscription.py     # SubscriptionPlan, Subscription, Transaction
│   ├── chat.py             # Conversation, ChatAgent, Iteration, ChatMessage
│   ├── settings.py         # UserSettings
│   ├── mcp_server.py       # MCPServer
│   ├── notification.py     # Notification, NotificationPreference
│   ├── admin.py            # AdminConfig, SystemPrompt, DomainRule
│   ├── api_key.py          # UserAPIKey (BYOK)
│   └── contact.py          # ContactRequest
│
├── schemas/                # Pydantic request/response schemas
│   ├── auth.py
│   ├── user.py
│   ├── chat.py
│   ├── settings.py
│   ├── mcp.py
│   ├── billing.py
│   ├── api_key.py
│   └── admin.py
│
├── routes/                 # Sanic blueprint route handlers
│   ├── auth.py             # /api/v1/auth/*
│   ├── user.py             # /api/v1/user/*
│   ├── chat.py             # /api/v1/chat/*
│   ├── settings.py         # /api/v1/settings/*
│   ├── mcp.py              # /api/v1/mcp-servers/*
│   ├── api_keys.py         # /api/v1/api-keys/*
│   ├── billing.py          # /api/v1/billing/*
│   ├── notifications.py    # /api/v1/notifications/*
│   ├── contact.py          # /api/v1/contact
│   └── admin.py            # /api/v1/admin/*
│
├── services/               # Business logic layer
│   ├── auth_service.py     # Registration, login, JWT, password
│   ├── ai_client.py        # OpenAI-compatible client factory (BYOK)
│   ├── ai_orchestrator.py  # Main generate → evaluate → rephrase loop
│   ├── generator.py        # Generator agent (+ search + MCP)
│   ├── evaluator.py        # Evaluator agent (scoring)
│   ├── reprompt.py         # Prompt rephrasing service
│   ├── mcp_service.py      # MCP client (Streamable HTTP / SSE): tools/list, tools/call
│   ├── billing_service.py  # Subscriptions, Stripe checkout/webhooks, demo renewals
│   ├── notification_service.py  # Multi-channel dispatch
│   ├── search_service.py   # Google Custom Search + domain rules
│   └── token_tracker.py    # Token usage tracking
│
├── middleware/              # Sanic middleware
│   ├── auth_middleware.py   # JWT auth + decorators (require_auth, require_admin, require_tier)
│   └── rate_limiter.py     # Tier-aware limits on generation requests (Redis optional)
│
├── utils/                  # Shared utilities
│   ├── crypto.py           # Fernet encryption for API keys
│   ├── email.py            # SMTP email sending + Jinja2 templates
│   ├── webhooks.py         # Slack / Teams webhooks
│   ├── responses.py        # Standardized JSON responses
│   ├── db_schema.py        # Create tables / back-fill new columns on startup
│   └── exceptions.py       # Custom exception hierarchy
│
├── templates/email/        # HTML email templates (Jinja2)
├── scripts/                # create_admin, delete_user, test_smtp, smoke_test
├── tests/                  # Test suite
│
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

## Quick Start

### 1. Environment

```bash
cp .env.example .env
# Set at least JWT_SECRET and ENCRYPTION_KEY (see comments in the file)
```

### 2. Docker (PostgreSQL + Redis + backend)

```bash
docker compose up -d
docker compose exec backend python scripts/create_admin.py you@example.com
```

### 3. Local development (SQLite, no services needed)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py                      # tables are created on first start
python scripts/create_admin.py you@example.com --password 'S3cure!Pass'
```

### 4. Tests

```bash
pytest                             # throwaway SQLite DB, fake AI providers
TEST_DB_ENGINE=postgres DB_HOST=localhost DB_NAME=accura_test DB_USER=accura DB_PASSWORD=... pytest
```

## API Endpoints

Interactive documentation is available at `/docs` on a running server.

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register (sends a 6-digit OTP) |
| POST | `/api/v1/auth/verify-otp` / `resend-otp` | Verify email with the OTP |
| POST | `/api/v1/auth/login` | Login (verified accounts only) |
| POST | `/api/v1/auth/refresh` | Exchange a refresh token |
| POST | `/api/v1/auth/forgot-password` / `reset-password` | Single-use password reset link |
| POST | `/api/v1/auth/verify-email-change` | Confirm a new email address |
| GET | `/api/v1/auth/check-username/<name>` | Username availability |
| POST | `/api/v1/contact` | Submit contact request |
| GET | `/api/v1/billing/plans` | List subscription plans |
| POST | `/api/v1/billing/webhook` | Stripe webhook (signature verified) |
| GET | `/api/v1/health` | Health check |

### Authenticated User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/me` | Current user and profile |
| PUT | `/api/v1/user/profile` | Update profile |
| POST | `/api/v1/auth/change-password` / `request-email-change` | Account security |
| POST | `/api/v1/chat` | Create conversation & start generation |
| GET | `/api/v1/chat` | List conversations (paginated) |
| GET | `/api/v1/chat/<id>` | Conversation with agents, iterations, messages |
| PATCH | `/api/v1/chat/<id>/rename` | Rename |
| POST | `/api/v1/chat/<id>/message` | Follow-up message |
| POST | `/api/v1/chat/<id>/agent` | Add an agent for an alternative answer |
| POST | `/api/v1/chat/<id>/retry` | Re-run the latest prompt |
| DELETE | `/api/v1/chat/<id>` | Delete conversation |
| GET/PUT | `/api/v1/settings` | User settings |
| CRUD | `/api/v1/mcp-servers/*` | MCP servers (+ `POST /<id>/test`) |
| CRUD | `/api/v1/api-keys/*` | BYOK API keys |
| GET | `/api/v1/billing/subscription` / `transactions` / `tokens` | Billing info |
| POST | `/api/v1/billing/subscribe` / `cancel` | Change plan |
| GET | `/api/v1/notifications` / `unread-count` | Notifications |
| PATCH/DELETE | `/api/v1/notifications/<id>[/read]` | Mark read / delete |

### Admin Only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/dashboard` | Revenue, users, tokens |
| GET/PUT | `/api/v1/admin/users/*` | User management |
| GET/PUT/DELETE | `/api/v1/admin/config[/<key>]` | Runtime config overrides |
| CRUD | `/api/v1/admin/system-prompts/*` | AI system prompts |
| CRUD | `/api/v1/admin/domain-rules/*` | Search domain rules |
| GET/PUT | `/api/v1/admin/plans/*` | Subscription plans |
| CRUD | `/api/v1/admin/mcp-servers/*` | Global MCP servers |
| GET/PUT | `/api/v1/admin/contact-requests/*` | Contact requests |
| POST | `/api/v1/admin/reload-config` | Reload config.yaml and env |

## Flow: Generate → Evaluate → Rephrase

1. User submits prompt → Conversation created with generator + evaluator agents
2. Generator produces response (optionally using search + MCP tools, with earlier turns as context)
3. Evaluator scores response (0-100)
4. If score < threshold → Reprompt AI rephrases prompt → Generator retries
5. Loop continues until threshold met or max iterations reached
6. If multiple agents: best-scoring response wins
7. User notified via configured channels; failures are reported in the chat with a retry option

## Configuration

The system is configurable at three levels:
1. **`config.yaml`** – Base configuration for Docker / self-hosted deployments
2. **Environment variables** – Override YAML settings (see `.env.example`)
3. **Admin panel** – Runtime overrides stored in the `admin_config` table, keyed by dotted config path (e.g. `evaluation.global_threshold`) and applied without a restart

## License

See [LICENSE](../LICENSE)
