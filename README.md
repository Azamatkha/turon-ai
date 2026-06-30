# 🏦 Turon-AI

Internal **AI assistant (chatbot) for the bank**. Employees log in and ask questions about bank
products, rules, and internal documents. UI in Uzbek / Russian.

Monorepo: **frontend** (React + TypeScript + Vite) and **backend** (FastAPI + PostgreSQL + Redis
+ RabbitMQ + Celery + nginx, all in Docker).

---

## Prerequisites

- **Docker Desktop** (must be running)
- **Node.js** (for the frontend)
- **make** — on Windows: `winget install --id GnuWin32.Make -e`, then add
  `C:\Program Files (x86)\GnuWin32\bin` to PATH and reopen the terminal.

> If a local PostgreSQL is already using port **5432**, stop it first
> (Windows: `Stop-Service postgresql-x64-18`) so the Docker DB can bind it.

---

## Run the backend

```bash
cd backend
cp .env.example .env        # configure (set CORS to the frontend origin, passwords)
make run-dev                # build & start: postgres, redis, rabbitmq, app, celery, nginx
make migrate                # apply database migrations
```

First time only (no migration files yet): generate the initial migration before `make migrate`:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.override.yml exec app alembic revision --autogenerate -m "init"
```

## Run the frontend

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API (Swagger) | http://localhost:8000/docs |
| RabbitMQ panel | http://localhost:15672 |

---

## Useful commands (run from `backend/`)

`DC = docker compose --env-file .env -f infra/docker-compose.yml`

| Command | What it does |
|---------|--------------|
| `make run-dev` | start in dev mode (auto-reload) |
| `make down` | stop |
| `DC down -v` | stop and wipe the database |
| `make migrate` | apply migrations |
| `make logs-app` | tail backend logs |

> `make migration` does not work on Windows (uses `read -p`). Generate migrations with the
> `... override.yml exec app alembic revision --autogenerate -m "msg"` command above (dev compose,
> so the file is saved on the host). After changing `POSTGRES_*`, run `DC down -v` first.

---

## Project structure

```
turon-ai/
├── backend/   # FastAPI: user (auth), chat, admin, core (ai, redis, db) · README inside
└── frontend/  # React: pages, components, services, locales, hooks
```
