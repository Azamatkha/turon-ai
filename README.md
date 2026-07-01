# 🏦 Turon-AI

Internal **AI assistant (chatbot) for the bank**. Employees register/log in and ask questions
about bank products, rules, and internal documents. UI in Uzbek (Latin/Cyrillic) and Russian.

Monorepo:
- **`frontend/`** — React + TypeScript + Vite (Login, Register, Chat, Admin).
- **`backend/`** — FastAPI + PostgreSQL + Redis + RabbitMQ + Celery + nginx, all in Docker.

### What works now
- Auth: register (full name / login / department / password), login by username, JWT + refresh.
- Chat: conversations & messages stored in PostgreSQL, per-user history, like/dislike on answers.
  (AI answering is Stage 2 — currently a placeholder reply.)
- Profile: user changes own password.
- Admin panel: user list (search + department filter), create/edit/delete users, reset a user's
  password, and a real-time dashboard (users, sessions, requests, online now, likes/dislikes,
  department share, weekly volume, recent activity).

---

## Prerequisites

- **Docker Desktop** (running)
- **Node.js** (frontend)
- **make** — Windows: `winget install --id GnuWin32.Make -e`, then add
  `C:\Program Files (x86)\GnuWin32\bin` to PATH and reopen the terminal.

> Docker's PostgreSQL binds host port **5432**. If a local PostgreSQL already uses it, stop it
> first (Windows: `Stop-Service postgresql-x64-18`).

---

## Run locally (for testing)

```bash
git clone <repo-url>
cd turon-ai
```

### Backend (`cd backend`)
```bash
cp .env.example .env        # then edit .env (see "Environment" below)
make deploy-dev             # build + start (dev, auto-reload) + apply migrations
make shell                  # create the first admin
python -m scripts.create_superadmin
exit
```
> Migrations are already committed in `backend/migrations/versions/`, so `make deploy-dev`
> (which runs `make migrate` = `alembic upgrade head`) creates the full schema. You do **not**
> need to generate migrations on a fresh clone.

### Frontend (`cd frontend`)
```bash
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

### URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API (Swagger) | http://localhost:8000/docs |
| RabbitMQ panel | http://localhost:15672 |

Log in with the superadmin (`SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` from `.env`).

---

## Environment (`backend/.env`)

Copied from `.env.example`. `.env` is git-ignored — never commit it. Fill at least:

| Variable | Notes |
|----------|-------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | DB credentials (Docker creates the DB with these). Avoid `@ : / #` in the password. |
| `POSTGRES_HOST` | keep `postgres` (the Docker service name), **not** `localhost`. |
| `REDIS_PASSWORD`, `RABBITMQ_PASSWORD` | infra passwords |
| `PROJECT_SECRET_KEY`, `JWT_*_SECRET_KEY` | **change to long random strings for the server** |
| `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` | first admin account |
| `CORS_ALLOWED_ORIGINS` | frontend origin, e.g. `["http://localhost:5173"]` locally, or the real domain on the server |
| `ANTHROPIC_API_KEY` | needed for real AI answers (Stage 2); can stay empty for now |

Frontend `.env`: `VITE_API_URL` = backend URL (local: `http://localhost:8000`; server: the API domain).

---

## Deploy to a server

On the server (Docker + Docker Compose installed), from `backend/`:

```bash
cp .env.example .env         # fill PRODUCTION secrets + CORS_ALLOWED_ORIGINS = your frontend domain
make deploy-prod             # build + down + up + migrate  (production image, gunicorn workers)
make shell && python -m scripts.create_superadmin && exit   # first time only
```
`make deploy-prod` applies the committed migrations automatically (`alembic upgrade head`).

Frontend (build static files, set the API URL at build time):
```bash
cd frontend
echo "VITE_API_URL=https://<your-api-domain>" > .env
npm install && npm run build     # output in frontend/dist/
```
Serve `frontend/dist/` with a static host / nginx (or `npm run preview` for a quick check).

> Backend is served by the app container on `APP_BACKEND_PORT` (8001), fronted by nginx on 8000.

---

## Useful commands (from `backend/`)

`DC = docker compose --env-file .env -f infra/docker-compose.yml`

| Command | What it does |
|---------|--------------|
| `make deploy-dev` | build + start (dev, auto-reload) + migrate |
| `make deploy-prod` | build + down + up + migrate (server) |
| `make down` | stop |
| `DC down -v` | stop and wipe the database (volumes) |
| `make migrate` | apply migrations (`alembic upgrade head`) |
| `make shell` | shell inside the app container |
| `make logs-app` | tail backend logs |

> When you change a DB **model**, generate a migration in dev mode (so the file is saved on the
> host) and **commit it**:
> `DC -f infra/docker-compose.override.yml exec app alembic revision --autogenerate -m "message"`
> then `make migrate`. (`make migration` doesn't work on Windows — it uses `read -p`.)

---

## Project structure

```
turon-ai/
├── backend/
│   ├── infra/            # docker-compose (+override), nginx, postgres configs
│   ├── migrations/       # Alembic migrations (committed)
│   ├── scripts/          # create_superadmin
│   └── src/              # FastAPI: user (auth), chat, admin, core (ai, redis, db)
└── frontend/
    └── src/              # pages, components, services, locales, hooks
```
