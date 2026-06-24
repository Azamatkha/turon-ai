# TuronBank AI Platform — Template for AI Services

![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Mypy](https://img.shields.io/badge/mypy-strict-success)

A production-ready **template / modular monolith** for building TuronBank's internal AI
services. Each department's use case (e.g. *autopay* overdue analysis, fraud signals,
scoring) lives as a self-contained **module** that exposes one or more endpoints: an
internal service POSTs data, the module runs an AI analysis, and returns a structured
result.

Instead of standing up a separate project, Dockerfile, and CI pipeline for every
department, you add a new module here and reuse the shared infrastructure (AI client,
database, cache, rate limiting, auth, error handling, observability).

## Why a modular monolith

- **Shared infrastructure, once.** The AI client with a model-fallback chain, Redis cache
  and rate limiter, Unit of Work, error handling and security headers are written once in
  `core/` and reused by every module. One fix, one place — not 30 repositories.
- **One deploy, one CI.** A single stack, pipeline, and set of dashboards instead of 30.
- **Easy to extract later.** Each module is isolated (router → usecase → repository), so a
  department can be split into its own service when (and only when) there is a real reason
  — different load profile, regulatory isolation, or a dedicated team.

## Tech Stack

**Backend:** FastAPI, Python 3.13, SQLAlchemy 2.0+ (async), Pydantic v2
**Database:** PostgreSQL, Alembic (migrations)
**Task Queue:** Celery, RabbitMQ (broker), Redis (result backend & cache)
**AI:** Anthropic Claude API (primary) with a configurable model-fallback chain; pluggable
provider config (Anthropic / Gemini)
**Infrastructure:** Docker Compose, Nginx, Gunicorn + Uvicorn workers
**Code Quality:** Mypy (strict), Ruff, pre-commit, Pytest, bandit / pip-audit / gitleaks in CI

## Architecture

```
src/
├── core/                 # Shared infrastructure (reused by every module)
│   ├── ai/               # AI client (Anthropic), fallback chain, JSON parsing
│   ├── database/         # BaseRepository, Unit of Work, sessions, filters
│   ├── email_service/    # Transactional email (FastAPI-Mail) + templates
│   ├── errors/           # Custom exceptions and handlers
│   ├── limiter/          # Redis Lua rate limiter with in-memory fallback
│   ├── redis/            # Cache backend, coders, route cache manager
│   └── patterns/         # Singleton, etc.
├── user/                 # Users, profiles
│   └── auth/             # JWT, refresh-token rotation, permissions, role matrix
├── system/               # Health check, time, AI diagnostic
└── main/                 # App wiring (config, lifespan, router registration)
    └── presentation.py   # ← register new department modules here
```

**Patterns:** Repository → Service / UseCase (business logic) → Router. Transactions are
managed via a Unit of Work (`ApplicationUnitOfWork`).

## Adding a new department module

Each module follows the same shape (see `src/user/` as a reference):

```
src/autopay/
├── routers.py        # POST /v1/autopay/analyze
├── schemas.py        # Pydantic request / response models
├── usecases/
│   └── analyze_overdue.py
├── prompts.py        # the department's AI prompt
├── repositories.py   # optional: persist results
└── models.py         # optional: ORM models
```

Then wire it up:

1. **Register the router** in [`src/main/presentation.py`](src/main/presentation.py) inside
   `include_routers()`:
   ```python
   from src.autopay import routers as autopay_routers

   v1_router.include_router(
       autopay_routers.router, prefix="/autopay", tags=["Autopay"]
   )
   ```
2. **Expose repositories** (if any) on the Unit of Work in
   [`src/core/database/uow/application.py`](src/core/database/uow/application.py):
   ```python
   @property
   def autopay(self) -> AutopayRepository:
       return self._get_repository(AutopayRepository)
   ```
3. **Register ORM models** (if any) in [`models/__init__.py`](models/__init__.py) so
   relationships and migrations pick them up, then `make migration && make migrate`.

### Recommendations for service-to-service modules

Most department endpoints are machine-to-machine (an internal service calls you), not
end-user facing. For those, prefer:

- **Service authentication** (API key / mTLS) rather than the user JWT flow.
- **Per-department rate limits and AI quotas** (use `core/limiter`) so one department can't
  exhaust the Anthropic budget for the others.
- **Prompt versioning and request/response logging** for auditability of AI decisions.

## API Endpoints (template baseline)

The template ships with auth and system endpoints; department modules add their own.

| Group | Method & Path | Description |
|-------|---------------|-------------|
| Auth | `POST /v1/users/auth/register` | Register a user |
| Auth | `POST /v1/users/auth/verification-email` *(send)* / `GET /v1/users/auth/verify` | Email verification |
| Auth | `POST /v1/users/auth/login` | Log in (access + refresh JWT) |
| Auth | `POST /v1/users/auth/login/refresh` | Rotate refresh → new access token |
| Auth | `POST /v1/users/auth/logout` | Invalidate the session |
| Auth | `POST /v1/users/auth/password/reset` / `PUT .../password/reset/confirm` | Password reset request & confirm |
| Users | `GET /v1/users/me` | Current user profile |
| Users | `PATCH /v1/users/me/password` | Change password |
| Users | `GET /v1/users/{user_id}` | User summary (requires `VIEW_USERS`) |
| System | `GET /health/` | Service & dependency health |
| System | `GET /time/` | Current UTC time |
| System | `GET /diagnostic` | AI provider connectivity ping |

Interactive docs: Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`.

## Quick Start

### 1. Configure

```bash
cp .env.example .env
```

Fill in at least:

- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `RABBITMQ_PASSWORD`
- `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_MODEL` / `ANTHROPIC_FALLBACK_MODELS`)
- `JWT_USER_SECRET_KEY`, `JWT_ADMIN_SECRET_KEY`, `JWT_VERIFY_SECRET_KEY`,
  `JWT_RESET_PASSWORD_SECRET_KEY`, `PROJECT_SECRET_KEY`
- `EMAIL_USER`, `EMAIL_PASSWORD` (SMTP for verification / reset emails)
- `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`

### 2. Start (Docker)

```bash
make deploy-prod      # build + start app, postgres, redis, rabbitmq, celery, nginx
make migrate          # apply database migrations
```

Create the superadmin:

```bash
make shell            # open a shell in the app container
python -m scripts.create_superadmin
```

The API is served by the app container on `APP_BACKEND_PORT` (default `8001`), fronted
by Nginx. Swagger UI: `http://localhost:8001/docs`.

For local development use `make deploy-dev` / `make run-dev`.

## Make Targets

| Target | Description |
|--------|-------------|
| `make build` / `make up` / `make down` | Build / start / stop containers |
| `make deploy-prod` / `make deploy-dev` | Build and start the prod / dev stack |
| `make restart` | Restart the stack |
| `make migration` / `make migrate` | Create / apply Alembic migrations |
| `make celery-worker` / `make stop-celery` | Manage Celery workers |
| `make shell` | Shell inside the app container |
| `make logs` / `make logs-app` / `make logs-celery` | Tail logs |
| `make lint` / `make check-lint` | Run Ruff + Mypy |
| `make test` / `make test-cov` / `make check-coverage` | Run Pytest / with coverage |
| `make req-compile` / `make req-sync-dev` / `make req-sync-prod` | Manage pip-tools deps |
| `make info` | Print stack info |

## Authentication & Security

- **JWT** access + refresh tokens with **refresh-token rotation** and reuse detection
  (atomic Redis Lua script); single-use verification / reset tokens tracked in Redis.
- **Argon2** password hashing with automatic rehash-on-login; dummy-hash verification to
  mitigate user-enumeration timing attacks.
- **Rate limiting** via a Redis Lua sliding window with an in-memory fallback.
- Security response headers + CSP, request timing & DB-error middleware, masked secrets
  in logs.
- CI: `bandit` (SAST), `pip-audit` (dependency CVEs), `gitleaks` (secret scanning),
  pre-commit hooks.

## Dependencies (pip-tools)

- Direct deps live in `infra/requirements/*.in`; lockfiles `infra/requirements/*.txt`
  are generated by `pip-compile`.
- Update lockfiles: `make req-compile`. Sync env: `make req-sync-dev` / `make req-sync-prod`.

## Environment Variables

See `.env.example` for the full list. Key groups: application & CORS, PostgreSQL, Redis,
RabbitMQ, JWT secrets & lifetimes, SMTP, AI (Anthropic / Gemini).
</content>
