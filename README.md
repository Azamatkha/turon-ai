# Turon-AI

**Internal chatbot for bank employees.**

Turon-AI helps bank employees find information about banking products much faster and makes
searching easier. Through the chatbot, employees can query across the bank's ~2000 internal
documents, which speeds up how they get answers and removes the manual search work.

The UI is available in Uzbek (Latin and Cyrillic) and Russian.

---

## Tech stack

**Backend**
- Python 3.13, FastAPI, Pydantic v2
- PostgreSQL (SQLAlchemy 2.0 async, Alembic migrations)
- Redis (caching, rate limiting, refresh-token rotation)
- RabbitMQ + Celery (background tasks)
- nginx (reverse proxy)
- Anthropic Claude (AI answering)
- JWT auth (access + refresh with rotation), Argon2 password hashing
- Docker / Docker Compose

**Frontend**
- React 18 + TypeScript
- Vite
- React Router 6
- CSS Modules
- GSAP (animation), react-icons / flag-icons
- Docker / Docker Compose

---

## Getting started

Clone the repository:

```bash
git clone <repo-url>
```

### Backend

From the `backend/` directory:

```bash
cp .env.example .env
```

Then edit `.env` and fill in the required values (DB credentials, secrets, first admin
account). Keep `POSTGRES_HOST=postgres` — it must match the Docker service name.

Build and start the stack, then create the first admin:

```bash
make deploy-dev             # build + start (dev, auto-reload) + apply migrations
```

```bash
make shell                  # open a shell inside the app container
```

```bash
python -m scripts.create_superadmin
```

```bash
exit
```

> Migrations are already committed, so `make deploy-dev` builds the full schema. You do not
> need to autogenerate migrations on a fresh clone.

### Frontend

From the `frontend/` directory:

```bash
docker compose up --build -d
```

### URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API (Swagger) | http://localhost:8000/docs |
| RabbitMQ panel | http://localhost:15672 |

Log in with the superadmin account you created above.

---

## Architecture

Monorepo with two independent applications.

```
turon-ai/
├── backend/          # FastAPI modular monolith
│   ├── infra/        # docker-compose, nginx, postgres, requirements
│   ├── migrations/   # Alembic migrations (committed)
│   ├── scripts/      # create_superadmin, helpers
│   └── src/
│       ├── core/     # shared infra: ai, database (repo + UoW), redis, limiter, errors
│       ├── user/     # users + auth (JWT, refresh rotation, permissions)
│       ├── chat/     # chat sessions, messages, votes
│       ├── admin/    # admin panel (user CRUD, dashboard)
│       ├── system/   # health, time, AI diagnostic
│       └── main/     # app wiring (config, lifespan, router registration)
└── frontend/         # React + TypeScript + Vite
    └── src/          # pages, components, services, hooks, locales, contexts
```

**Backend** is a modular monolith. Each use case is a self-contained module following a
`Repository → UseCase → Router` layering, reusing shared infrastructure from `core/`.
Business logic stays out of the routers, database transactions are handled through a Unit of
Work, and all business routes live under the `/v1/...` prefix.

**Frontend** is a single-page React application (Login, Register, Chat, Admin). The API layer
lives in `src/services/`, authenticated requests auto-retry once on a `401` by rotating the
refresh token, and all user-facing text is localized in `src/locales/` (Uzbek Latin, Uzbek
Cyrillic, Russian).
