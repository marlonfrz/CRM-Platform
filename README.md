# CRM Platform

Private CRM core for individual professionals and organizations.

## Prerequisites

- Docker with Docker Compose
- Node.js 22 or newer for running the frontend outside Docker
- Python 3.12 or newer for running the backend outside Docker

## Start with Docker

```bash
docker compose up --build
```

Apply database migrations from another terminal before using the application:

```bash
docker compose exec backend alembic upgrade head
```

Services:

- frontend: <http://localhost:3000>
- backend OpenAPI: <http://localhost:8000/docs>
- backend liveness: <http://localhost:8000/api/v1/health/live>
- backend readiness: <http://localhost:8000/api/v1/health/ready>
- development email inbox: <http://localhost:8025>

Copy `.env.example` to `.env` before changing the development defaults. Never reuse the example password in production.
Mailpit captures development emails locally; it does not deliver them to real recipients.

## Validation

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm test
```

Backend:

```bash
cd backend
python -m venv .venv
python -m pip install -e ".[dev]"
docker compose up -d database
alembic upgrade head
ruff check .
mypy app
pytest
```

The frontend response types in `frontend/src/lib/api-generated/` are generated from FastAPI OpenAPI. After changing a backend response schema, install the backend environment and run `npm run generate:api` from `frontend/`, then commit the regenerated types. This command does not need a running API or database. Set `CRM_PYTHON` if the backend virtual environment is in a nonstandard location.

Initialize the first organization and owner after applying migrations:

```bash
cd backend
crm-bootstrap --mode BUSINESS --organization-name "Example Company" --owner-name "Owner Name" --owner-email owner@example.com
```

Use `INDIVIDUAL` instead of `BUSINESS` for a single-person installation. The command prompts for the password without echoing it. User invitations created in the Docker development environment are available in Mailpit.

## Optional AI summaries

Owners and department admins can access `/summaries`, or open a client summary from its detail page. AI is disabled by default; the CRM works without it. The owner can configure Ollama, OpenAI, Anthropic Claude or Google Gemini from `IA > Opciones`; external tokens are encrypted per organization and never returned by the API. Production must set a stable `AI_CREDENTIALS_ENCRYPTION_KEY`.

For local tests, start the optional private Ollama service and download the recommended model:

```bash
docker compose --profile ai up -d ollama
docker compose --profile ai exec ollama ollama pull llama3.2:1b
```

See [AI_SUMMARIES.md](docs/AI_SUMMARIES.md) for privacy, limits, model choices, demo data and acceptance checks.

## Portfolio demo

The `demo` branch runs the same Next.js CRM screens and routes with synthetic, session-scoped data. It starts without the API, PostgreSQL or an AI provider. See [demo/README.md](demo/README.md) for local and Docker instructions. Demo edits are temporary and reset when the server restarts.

## Production preparation

Production uses versioned frontend and backend images, `compose.production.yaml` and Caddy as the only public entry point. It is intentionally separate from the local development stack. See [PRODUCTION.md](docs/PRODUCTION.md) for installation, migrations, HTTPS, backups, restore checks, updates and rollback.

Customer-specific functionality does not use permanent branches or custom images. See [FEATURE_VARIANTS.md](docs/FEATURE_VARIANTS.md) for the shared-release and optional-capability policy.
