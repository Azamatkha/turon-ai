# Turon AI — Backend

![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)

**Turon AI** — Turon Bank xodimlari uchun ichki AI yordamchi. Tizim bankning
ichki hujjatlarini (1700–2000 ta skannerlangan PDF, o'zbek/rus tilida) o'qiydi
va ular asosida savollarga javob beradi (RAG — retrieval-augmented generation).

Loyiha kuchli FastAPI infratuzilma shabloni ustiga qurilgan (PostgreSQL, Redis,
Celery, RabbitMQ, Nginx, Docker, migratsiyalar, testlar). Biznes mantiq Turon AI
uchun moslangan: **RAG quvuri** va **oddiy autentifikatsiya**.

> Kod va izohlar (RAG va auth qismida) o'zbek tilida yozilgan.

---

## Mundarija

- [Arxitektura](#arxitektura)
- [RAG oqimi](#rag-oqimi)
- [Texnologiyalar](#texnologiyalar)
- [O'rnatish va ishga tushirish](#ornatish-va-ishga-tushirish)
- [Muhit o'zgaruvchilari (.env)](#muhit-ozgaruvchilari-env)
- [Ma'lumotlar bazasi (PostgreSQL)](#malumotlar-bazasi-postgresql)
- [Hujjatlarni yuklash (ingest)](#hujjatlarni-yuklash-ingest)
- [API endpointlar](#api-endpointlar)
- [Autentifikatsiya oqimi](#autentifikatsiya-oqimi)
- [Frontend integratsiyasi](#frontend-integratsiyasi)
- [Deployment](#deployment)
- [Papkalar tuzilishi](#papkalar-tuzilishi)

---

## Arxitektura

```
Frontend (React)
      │  POST /api/v1/auth/login        (oddiy auth, JWT)
      │  POST /api/v1/ask               (savol -> AI javob)
      ▼
Nginx ──► FastAPI (app)
                ├── simple_auth/   login / logout / me        ─► PostgreSQL (users)
                ├── ask/           RAG savol-javob            ─► Qdrant + LLM
                ├── rag/           OCR, chunking, embeddings, retriever, ingest
                ├── user/, system/ (shablon, o'z holicha qoldirilgan)
                └── core/          AI mijoz, DB, Redis, errors, middleware, ...
```

Eslatma: shablonning kengaytirilgan auth tizimi (`src/user`, refresh token, RBAC,
email tasdiqlash) **o'chirilmagan** — kelajak uchun joyida turadi. Frontend esa
yangi, sodda `src/simple_auth` endpointlaridan foydalanadi.

---

## RAG oqimi

```
INGEST (CLI):   ingest -> ocr -> chunking -> embeddings -> Qdrant
SO'ROV (API):   /api/v1/ask -> retriever -> Qdrant -> LLM (Anthropic) -> javob + manbalar
```

- **OCR** (`rag/ocr.py`) — skaner PDF rasmga aylantiriladi, tozalanadi
  (grayscale → kontrast → Otsu binarizatsiya), `tesseract` (`uzb+rus`) o'qiydi.
- **Chunking** (`rag/chunking.py`) — ~800 belgilik bo'laklar, 150 belgi ustma-ust;
  1-betdan hujjat sarlavhasi aniqlanadi.
- **Embeddings** (`rag/embeddings.py`) — `BAAI/bge-m3` (1024-o'lchamli vektor).
- **Qdrant** (`rag/qdrant_client.py`) — `turon_docs` kolleksiyasi (COSINE).
- **Retriever** (`rag/retriever.py`) — savolga eng yaqin `top_k` bo'lak.
- **LLM** (`ask/service.py`) — shablondagi Anthropic mijozi orqali, faqat topilgan
  kontekst asosida javob (manbalar bilan).

---

## Texnologiyalar

| Soha            | Texnologiya                                  |
|-----------------|----------------------------------------------|
| Veb / API       | FastAPI, Uvicorn/Gunicorn, Pydantic v2       |
| Auth            | PyJWT, argon2 (oddiy: bitta access token)    |
| Baza            | PostgreSQL, SQLAlchemy (async), Alembic      |
| Vektor baza     | Qdrant                                        |
| OCR             | pdf2image (poppler), pytesseract (tesseract) |
| Embeddings      | sentence-transformers (bge-m3)               |
| LLM             | Anthropic (claude-opus-4-8 + fallback)       |
| Kesh / Navbat   | Redis, Celery, RabbitMQ                       |
| Infra           | Docker, Docker Compose, Nginx, Makefile      |

---

## O'rnatish va ishga tushirish

> Yagona talab: Docker + Docker Compose.

### To'liq ilova — bitta buyruq (loyiha ildizidan)

```bash
docker compose up --build
```

Bu hamma narsani ko'taradi: **postgres + redis + rabbitmq + qdrant + backend +
celery + frontend**. Backend avtomatik ravishda migratsiya qiladi va standart
foydalanuvchini (`.env`dagi `SUPER_ADMIN_*`) yaratadi — qo'shimcha qadam shart emas.

- Frontend:         http://localhost:5173
- API / Swagger:    http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

> Birinchi build embeddings uchun torch o'rnatadi — 5-10 daqiqa olishi mumkin.
> `.env` allaqachon ishlaydigan qiymatlar bilan to'ldirilgan (login testi uchun
> maxfiy kalitlar shart emas; ANTHROPIC_API_KEY faqat `/ask` uchun kerak).

Standart login:  `admin` / `admin123`  (`.env`dagi `SUPER_ADMIN_*`).

### Tez lokal test (venv) — faqat backend + login

Docker image'ni (torch) build qilmasdan login'ni tekshirish uchun:

```bash
# 1) faqat baza va kesh (docker)
docker run -d --name turon-pg    -e POSTGRES_USER=turon -e POSTGRES_PASSWORD=7711 \
    -e POSTGRES_DB=turon-ai-db -p 5433:5432 postgres:18
docker run -d --name turon-redis -p 6380:6379 redis:7 redis-server --requirepass devpass

# 2) venv + kerakli kutubxonalar (torch'siz — /ask uchun keyin o'rnatiladi)
cd backend
python -m venv venv && source venv/Scripts/activate   # Linux/Mac: source venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings python-dotenv \
    python-multipart pyjwt "passlib[argon2]" argon2-cffi httpx sqlalchemy asyncpg \
    alembic alembic-postgresql-enum redis celery email-validator fastapi-mail uuid6 asgiref

# 3) migratsiya + foydalanuvchi + server  (.env hostlari localhost:5433 / 6380 bo'lsin)
alembic upgrade head
python -m scripts.seed_user
uvicorn src.main.web:app --host 0.0.0.0 --port 8000
```

Foydali `make` buyruqlari (backend stack uchun): `make up`, `make down`, `make logs`,
`make migrate`, `make shell`, `make test`. To'liq ro'yxat: `make info`.

---

## Muhit o'zgaruvchilari (.env)

Eng muhimlari (to'liq ro'yxat — `.env.example`):

| O'zgaruvchi          | Tavsif                                                |
|----------------------|-------------------------------------------------------|
| `ANTHROPIC_API_KEY`  | LLM javob berishi uchun **shart**                     |
| `POSTGRES_DB`        | `turon-ai-db`                                          |
| `POSTGRES_USER`      | DB foydalanuvchisi                                     |
| `POSTGRES_PASSWORD`  | `7711` (namuna)                                        |
| `JWT_USER_SECRET_KEY`| Access token maxfiy kaliti (production'da almashtiring)|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token amal qilish muddati                    |
| `SUPER_ADMIN_USERNAME` / `_PASSWORD` / `_EMAIL` / `_PHONE` | Seed foydalanuvchi |
| `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_COLLECTION` | Vektor baza            |
| `EMBEDDING_MODEL`    | `BAAI/bge-m3`                                          |
| `OCR_LANGUAGES`      | `uzb+rus` (kirill uchun `uzb_cyrl+rus`)               |
| `RAG_TOP_K`          | Har savolga nechta bo'lak olinadi (standart 5)        |

---

## Ma'lumotlar bazasi (PostgreSQL)

PostgreSQL faqat **foydalanuvchilar / autentifikatsiya** uchun ishlatiladi.
Vektorlar **Qdrant**'da saqlanadi (PostgreSQL'da emas).

```bash
make migrate                  # jadvallarni yaratadi
make migration message="..."  # model o'zgarsa yangi migratsiya
```

Boshlang'ich migratsiya: `migrations/versions/0001_initial_users.py` (`users` jadvali).

---

## Hujjatlarni yuklash (ingest)

PDF'larni `backend/data/documents/` ichiga qo'ying, so'ng:

```bash
docker compose --env-file .env -f infra/docker-compose.yml run --rm app \
    python -m src.rag.ingest
```

`bge-m3` modeli (~2.3 GB) birinchi ishlatishda `turon-hf-models` volume'iga bir
marta yuklanadi. Vektor qidiruvni tekshirish:

```bash
... run --rm app python -m src.rag.retriever "PQ-500 qaror"
```

---

## API endpointlar

Turon AI endpointlari `/api/v1` ostida:

| Metod | Yo'l                     | Tavsif                              | Auth |
|-------|--------------------------|-------------------------------------|------|
| GET   | `/health/`               | Server tirikmi                      | yo'q |
| POST  | `/api/v1/auth/login`     | Login → JWT access token            | yo'q |
| POST  | `/api/v1/auth/logout`    | Logout (token mijozda o'chiriladi)  | ha   |
| GET   | `/api/v1/auth/me`        | Joriy foydalanuvchi                 | ha   |
| POST  | `/api/v1/ask`            | Savol → AI javob + manbalar         | ha   |

Misol:

```bash
# 1) Login
curl -X POST localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"<username>","password":"<parol>"}'

# 2) Savol (yuqoridagi access_token bilan)
curl -X POST localhost:8000/api/v1/ask \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"savol":"Ichki nazorat tartibi qanday?"}'
```

> Eslatma: shablonning kengaytirilgan auth'i hamon `/v1/users/auth/*` da mavjud,
> lekin frontend uchun sodda `/api/v1/auth/*` ishlatiladi.

---

## Autentifikatsiya oqimi

Oddiy va stateless:

1. Frontend `POST /api/v1/auth/login` ga `{login, password}` yuboradi.
2. Backend foydalanuvchini PostgreSQL'dan topadi, parolni (argon2) tekshiradi.
3. Bitta **JWT access token** qaytariladi (`config.jwt` sozlamalari bilan).
4. Frontend tokenni saqlaydi va himoyalangan so'rovlarda
   `Authorization: Bearer <token>` yuboradi.
5. `GET /api/v1/auth/me` token bo'yicha foydalanuvchini qaytaradi; `logout`
   stateless (token mijozda o'chiriladi).

RBAC, refresh token va email tasdiqlash **yo'q** (kerak bo'lsa, shablonning
`src/user/auth` tizimi tayyor turibdi).

---

## Frontend integratsiyasi

- `frontend/src/services/authService.ts` — `login` / `logout` / token saqlash.
- `frontend/src/pages/LoginPage.tsx` — login muvaffaqiyatli bo'lsa `/chat` ga o'tadi.
- API manzili: `VITE_API_URL` (standart `http://localhost:8000`).

---

## Deployment

```bash
make deploy-prod      # build -> down -> up -> migrate
# so'ng bir marta:
docker compose ... exec app python -m scripts.seed_user
docker compose ... run --rm app python -m src.rag.ingest
```

Nginx 8000-portda tinglaydi va `app` (8001) ga uzatadi.

---

## Papkalar tuzilishi

```
backend/
├── src/
│   ├── simple_auth/   # Turon AI: oddiy auth (login/logout/me)
│   ├── ask/           # Turon AI: RAG savol-javob (/api/v1/ask)
│   ├── rag/           # OCR, chunking, embeddings, qdrant, retriever, ingest
│   ├── core/          # AI mijoz, DB, Redis, errors, middleware (shablon)
│   ├── user/, system/ # shablon (o'z holicha qoldirilgan)
│   └── main/          # FastAPI app, config, presentation (router'lar)
├── migrations/        # Alembic
├── scripts/           # seed_user, check_env, ...
├── infra/             # docker, docker-compose, nginx, requirements
└── tests/
```
```
