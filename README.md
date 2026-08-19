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

Services:

- frontend: <http://localhost:3000>
- backend OpenAPI: <http://localhost:8000/docs>
- backend liveness: <http://localhost:8000/api/v1/health/live>
- backend readiness: <http://localhost:8000/api/v1/health/ready>

Copy `.env.example` to `.env` before changing the development defaults. Never reuse the example password in production.

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

Initialize the first organization and owner after applying migrations:

```bash
cd backend
crm-bootstrap --mode BUSINESS --organization-name "Example Company" --owner-name "Owner Name" --owner-email owner@example.com
```

Use `INDIVIDUAL` instead of `BUSINESS` for a single-person installation. The command prompts for the password without echoing it. Email delivery and user invitations are intentionally deferred to the authentication phase.
