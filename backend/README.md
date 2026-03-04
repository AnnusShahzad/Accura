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
│   ├── mcp_service.py      # MCP server CRUD & calling
│   ├── billing_service.py  # Subscriptions, transactions
│   ├── notification_service.py  # Multi-channel dispatch
│   ├── search_service.py   # Google Custom Search + domain rules
│   └── token_tracker.py    # Token usage tracking
│
├── middleware/              # Sanic middleware
│   ├── auth_middleware.py   # JWT auth + decorators (require_auth, require_admin, require_tier)
│   └── rate_limiter.py     # Tier-aware rate limiting
│
├── utils/                  # Shared utilities
│   ├── crypto.py           # Fernet encryption for API keys
│   ├── email.py            # SMTP email sending + Jinja2 templates
│   ├── webhooks.py         # Slack / Teams webhooks
│   ├── responses.py        # Standardized JSON responses
│   └── exceptions.py       # Custom exception hierarchy
│
├── templates/email/        # HTML email templates (Jinja2)
├── migrations/             # Piccolo database migrations
├── tests/                  # Test suite
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Docker (Recommended)

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, runs migrations, and launches the backend.

### 3. Local Development

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt

# Run migrations
piccolo migrations forwards accura

# Start server
python app.py
```

### 4. Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new account |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh JWT tokens |
| POST | `/api/v1/auth/verify-email` | Verify email address |
| POST | `/api/v1/contact` | Submit contact request |
| GET | `/api/v1/billing/plans` | List subscription plans |
| GET | `/api/v1/health` | Health check |

### Authenticated User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/me` | Get current user |
| PUT | `/api/v1/user/profile` | Update profile |
| POST | `/api/v1/chat/` | Create conversation & start AI |
| GET | `/api/v1/chat/` | List conversations |
| GET | `/api/v1/chat/<id>` | Get conversation detail |
| PATCH | `/api/v1/chat/<id>/rename` | Rename conversation |
| POST | `/api/v1/chat/<id>/agent` | Add agent mid-chat |
| DELETE | `/api/v1/chat/<id>` | Archive conversation |
| GET | `/api/v1/settings/` | Get user settings |
| PUT | `/api/v1/settings/` | Update user settings |
| CRUD | `/api/v1/mcp-servers/*` | Manage MCP servers |
| CRUD | `/api/v1/api-keys/*` | Manage BYOK API keys |
| GET | `/api/v1/billing/subscription` | Get subscription |
| POST | `/api/v1/billing/subscribe` | Subscribe to plan |
| POST | `/api/v1/billing/cancel` | Cancel subscription |
| GET | `/api/v1/billing/transactions` | Transaction history |
| GET | `/api/v1/billing/tokens` | Token usage |
| GET | `/api/v1/notifications/` | List notifications |
| PATCH | `/api/v1/notifications/<id>/read` | Mark as read |

### Admin Only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/dashboard` | Revenue & user stats |
| CRUD | `/api/v1/admin/users/*` | User management |
| GET/PUT | `/api/v1/admin/config` | Dynamic config |
| GET/PUT | `/api/v1/admin/system-prompts` | AI system prompts |
| CRUD | `/api/v1/admin/domain-rules/*` | Search domain rules |
| GET/PUT | `/api/v1/admin/plans/*` | Subscription plans |
| CRUD | `/api/v1/admin/mcp-servers/*` | Global MCP servers |
| GET/PUT | `/api/v1/admin/contact-requests/*` | Contact requests |
| POST | `/api/v1/admin/reload-config` | Hot-reload YAML config |

## Flow: Generate → Evaluate → Rephrase

1. User submits prompt → Conversation created with generator + evaluator agents
2. Generator produces response (optionally using search + MCP tools)
3. Evaluator scores response (0-100)
4. If score < threshold → Reprompt AI rephrases prompt → Generator retries
5. Loop continues until threshold met or max iterations reached
6. If multiple agents: best-scoring response wins
7. User notified via configured channels

## Configuration

The system is configurable at three levels:
1. **`config.yaml`** – Base configuration for Docker / self-hosted deployments
2. **Environment variables** – Override YAML settings (see `.env.example`)
3. **Admin panel** – Runtime overrides stored in `admin_config` table

## License

See [LICENSE](../LICENSE)
