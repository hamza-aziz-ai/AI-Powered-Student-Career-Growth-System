# Career Growth AI for Kids

Parents create an account, add their child's profile (name, age/grade, interests, strengths), and get AI-generated career-exploration insights for that child. Children never have their own login — parents own and control all data.

**Stack:** FastAPI (Python) · PostgreSQL · React + TypeScript (Vite) · Ollama (`gpt-oss:120b-cloud`) for insight generation.

## Prerequisites

- Python 3.14 with [pipenv](https://pipenv.pypa.io/)
- Node.js (LTS) with npm
- A locally installed PostgreSQL server (not Docker, for now — `docker-compose.yml` is kept in the repo for later but isn't used in this phase of development)
- [Ollama](https://ollama.com/) running locally with the model pulled: `ollama pull gpt-oss:120b-cloud`

## First-time setup

1. Create a dedicated app role and databases in your local Postgres (connect as your `postgres` superuser, e.g. `psql -U postgres -h localhost`):
   ```sql
   CREATE USER career_growth_app WITH PASSWORD 'your-password-here';
   CREATE DATABASE career_growth OWNER career_growth_app;
   CREATE DATABASE career_growth_test OWNER career_growth_app;  -- used by pytest
   ```
2. Copy the env file, fill in the password from step 1 and a real JWT secret:
   ```
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"   # paste into JWT_SECRET_KEY
   ```
3. Install backend dependencies and run migrations:
   ```
   pipenv install --dev
   cd backend
   pipenv run alembic upgrade head
   ```
4. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```

## Running locally

Backend (from `backend/`):
```
pipenv run uvicorn app.main:app --reload --port 8000
```

Frontend (from `frontend/`):
```
npm run dev
```

The Vite dev server (http://localhost:5173) proxies `/api` to the backend on port 8000, so cookies and CORS work the same as in production. Make sure `ollama serve` is running before generating insights.

`GET /api/health` reports liveness only; `GET /api/ready` also checks PostgreSQL and Ollama and returns 503 if either is down. The interactive API docs (`/docs`, `/redoc`, `/openapi.json`) are only served when `ENVIRONMENT=development`. Outside development the backend refuses to start unless `JWT_SECRET_KEY` is a real random secret of at least 32 characters. `ENVIRONMENT` defaults to `development`, which also turns off the `Secure` cookie flag, so any deployment must set `ENVIRONMENT` to something else (for example `production`).

## Tests

Backend (from `backend/`, requires Postgres running — a `<db>_test` database is created automatically):
```
pipenv run pytest
```

Frontend (from `frontend/`):
```
npm run test
```

## Project layout

```
backend/app/        FastAPI app: routers, services, models, schemas
backend/alembic/     Database migrations
backend/tests/       pytest suite (unit + integration)
frontend/src/        React app: pages, routes, api client, auth context
docker-compose.yml   Postgres via Docker — not currently used, kept for later
```

## Data privacy notes

- Children never authenticate directly; only parents have accounts.
- Child profiles collect only what's needed for insights: first name, birth **year** (not full DOB), grade, interest/strength tags, optional notes — no photos, no school name.
- The AI prompt sent to Ollama contains only an approximate age, the grade level, and the interest, strength and favorite-subject tags, since `gpt-oss:120b-cloud` is a cloud-hosted model and that request leaves the machine. It never includes the child's name or the parent's private notes. Grade and tags are still parent-typed text, so this is data minimisation rather than anonymisation; the child form tells parents not to put identifying details there.
- Auth uses httpOnly, Secure (in non-dev environments), SameSite=Strict cookies — tokens are never exposed to frontend JavaScript.
- Application logs never include child PII (name, notes, profile snapshots, or AI output) — see `backend/app/core/logging.py`.
