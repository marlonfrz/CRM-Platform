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
ruff check .
mypy app
pytest
```
