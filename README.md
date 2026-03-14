# Accura

An AI response orchestration platform that iteratively generates, evaluates, and refines responses until quality thresholds are met. Built for self-hosted deployments with bring-your-own-key (BYOK) support.

## What It Does

Accura implements a generate-evaluate-refine loop for AI responses:

1. **Generate** – Creates responses using configurable AI models with optional web search and MCP tool integration
2. **Evaluate** – Scores responses against quality criteria
3. **Refine** – Rephrases prompts and regenerates until threshold is met or iteration limit reached

The system supports multiple generator agents per conversation, tier-based rate limiting, and subscription management.

## Tech Stack

**Backend**
- Sanic (async web framework)
- Piccolo ORM (PostgreSQL)
- JWT authentication with bcrypt
- Redis for rate limiting
- SMTP email with Jinja2 templates

**Frontend**
- Next.js 16 (App Router)
- React 19
- shadcn/ui components
- TanStack Query
- Zustand for state management

## Project Structure

```
accura/
├── backend/
│   ├── models/          # Database tables (User, Subscription, Conversation, etc.)
│   ├── routes/          # API endpoints grouped by feature
│   ├── services/        # Business logic (orchestrator, generator, evaluator)
│   ├── middleware/      # Auth, rate limiting
│   ├── schemas/         # Pydantic validation
│   └── utils/           # Email, crypto, webhooks
│
└── frontend/
    ├── src/app/         # Next.js routes (auth, dashboard, chat)
    ├── components/      # React components
    ├── hooks/           # Custom React hooks
    └── stores/          # Zustand stores
```

## Monorepo Commands (Root)

The repository now supports running backend and frontend from the root as a single workspace.

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for Postgres + Redis)

### 1. Install Dependencies

From the repository root:

```bash
npm install
```

Then install backend Python dependencies (use your active virtual environment):

```bash
npm run setup:backend
```

Or run both setup steps:

```bash
npm run setup
```

### 2. Start Local Infra (Optional)

```bash
npm run dev:infra
```

This starts PostgreSQL + Redis from `backend/docker-compose.yml`.

### 3. Run Both Apps With One Command

```bash
npm run dev
```

This launches:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### 4. Other Root Scripts

- `npm run dev:backend` – run only backend
- `npm run dev:frontend` – run only frontend
- `npm run build` – build frontend
- `npm run lint` – lint frontend
- `npm run stop:infra` – stop infra services

## Setup

### Prerequisites

- Docker and Docker Compose (recommended)
- Or: Python 3.11+, Node.js 20+, PostgreSQL 15+, Redis

### Quick Start with Docker

1. Clone and configure:
```bash
git clone <repository-url>
cd accura
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Edit `backend/.env` with your credentials:
```env
APP_SECRET_KEY=<generate-with-openssl-rand-hex-32>
DB_PASSWORD=<secure-password>
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=<your-email>
SMTP_PASSWORD=<your-password>
DEFAULT_AI_MODEL=gpt-4o
DEFAULT_AI_API_KEY=<your-openai-key>
```

3. Start services:
```bash
cd backend
docker compose up -d
```

This starts PostgreSQL, Redis, runs migrations, and launches the API at `http://localhost:8000`.

4. Start frontend:
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure database in config.yaml or .env
piccolo migrations forward
python app.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Configuration uses a layered approach:

1. `backend/config.yaml` – defaults for self-hosted deployments
2. Environment variables – override YAML values
3. Database settings – per-user and per-conversation overrides

Key environment variables:

```env
# App
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
APP_SECRET_KEY=<required>
APP_FRONTEND_URL=http://localhost:3000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=accura
DB_USER=accura
DB_PASSWORD=<required>

# AI (defaults, users can BYOK)
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o
DEFAULT_AI_API_KEY=<required>

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<required>
SMTP_PASSWORD=<required>
SMTP_FROM_EMAIL=noreply@example.com

# Optional: Search
GOOGLE_CUSTOM_SEARCH_API_KEY=<key>
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=<id>

# Optional: Webhooks
SLACK_WEBHOOK_URL=<url>
```

## API Overview

All endpoints are under `/api/v1/`:

- **auth** – register, login, verify email, OTP, password reset
- **user** – profile management
- **chat** – conversations, messages, streaming responses
- **settings** – quality thresholds, models, notification preferences
- **api-keys** – BYOK key management (encrypted)
- **mcp-servers** – MCP server configuration and tool access
- **billing** – subscriptions, transactions, Stripe webhooks
- **notifications** – push notifications
- **admin** – system prompts, domain rules, analytics

Authentication uses Bearer tokens. Protected routes require `Authorization: Bearer <token>`.

## Features

### AI Orchestration

- Iterative generate-evaluate-refine loop with configurable quality thresholds
- Multiple generator agents per conversation
- Token usage tracking across iterations
- Timeout protection with graceful degradation

### Bring Your Own Key (BYOK)

Users can provide their own API keys for:
- OpenAI
- Anthropic
- Google AI
- Custom OpenAI-compatible endpoints

Keys are encrypted at rest using Fernet symmetric encryption.

### MCP Integration

Connect external tools via Model Context Protocol servers:
- User-configured MCP servers
- Automatic tool discovery
- Request/response logging
- Error handling with fallbacks

### Subscription System

- Tiered plans with feature gates (search, MCP, max iterations)
- Stripe integration for payments
- Recurring billing with APScheduler
- Transaction history and invoice management

### Web Search

- Google Custom Search integration
- Domain-specific filtering rules
- Automatic relevance pruning
- Search result caching

## Development

### Running Tests

```bash
cd backend
pytest tests/
```

Tests cover:
- Authentication flows
- Chat orchestration
- Settings management
- E2E API interactions

### Database Migrations

```bash
# Create migration
piccolo migrations new

# Apply migrations
piccolo migrations forward

# Rollback
piccolo migrations backward
```

### Utilities

- **fix_db.py** – repair database inconsistencies
- **delete_user.py** – GDPR-compliant user deletion
- **test_smtp.py** – verify email configuration

## Deployment

### Docker Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment Checklist

- [ ] Set strong `APP_SECRET_KEY`
- [ ] Configure production database with connection pooling
- [ ] Set up Redis for rate limiting
- [ ] Configure SMTP for transactional emails
- [ ] Add Stripe webhook endpoint with signature verification
- [ ] Set `APP_ENV=production` and `APP_DEBUG=false`
- [ ] Configure CORS for your frontend domain
- [ ] Set up SSL/TLS termination (nginx/Caddy)
- [ ] Enable database backups
- [ ] Configure logging and monitoring

## License

See [LICENSE](LICENSE) for details.

## Support

For self-hosted deployment issues, check:
- Backend logs: `docker compose logs backend`
- Database status: `docker compose ps postgres`
- Configuration: review `.env` and `config.yaml`

Email: support@accura.ai (if configured in branding settings)
