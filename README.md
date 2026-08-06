# Turon-AI

**Turonbank xodimlari uchun ichki AI yordamchi (chatbot).**

Xodim ro'yxatdan o'tadi, tizimga kiradi va bank mahsulotlari, ichki hujjatlar,
filiallar hamda xodimlar ma'lumotnomasi bo'yicha savol beradi. Javob bank o'zining
ma'lumotlaridan olinadi — bot hech narsani "o'ylab topmaydi".

Maqsad: xodim kerakli ma'lumotni qidirib o'tirmasin. Ilgari ~2000 ta ichki hujjat va
sayt sahifalari bo'ylab qo'lda qidirishga ketadigan vaqt savol-javobga aylanadi.

Interfeys uch tilda: **o'zbekcha (lotin)**, **o'zbekcha (kirill)**, **ruscha**.

---

## Mundarija

- [Qanday ishlaydi](#qanday-ishlaydi)
- [Texnologiyalar](#texnologiyalar)
- [Arxitektura](#arxitektura)
- [Tez boshlash](#tez-boshlash)
- [Portlar va manzillar](#portlar-va-manzillar)
- [Kundalik buyruqlar](#kundalik-buyruqlar)
- [Admin bilan ishlash](#admin-bilan-ishlash)
- [Ma'lumotlar bazasi (PostgreSQL)](#malumotlar-bazasi-postgresql)
- [Vektor baza (Qdrant)](#vektor-baza-qdrant)
- [Bilim bazasini to'ldirish](#bilim-bazasini-toldirish)
- [Testlar va kod sifati](#testlar-va-kod-sifati)
- [Muammolarni bartaraf etish](#muammolarni-bartaraf-etish)

---

## Qanday ishlaydi

Savol javobga aylanguncha bosqichlar (`backend/src/knowledge/`):

```
Foydalanuvchi savoli
   │
   ├─ 1. Alifbo aniqlanadi (kirill/lotin) va ichkarida lotinga o'giriladi
   │
   ├─ 2. TUSHUNISH — QuestionRouter (router.py)
   │     LLM savol turini aniqlaydi: xodim / mahsulot / filial / kurs /
   │     salomlashish / bot haqida. Salomlashishga shu yerda javob beriladi
   │     (bazaga umuman borilmaydi).
   │
   ├─ 3a. XODIM savoli  ->  deterministik qidiruv (usecases.py)
   │      IP raqam, telefon, F.I.SH yoki bo'lim bo'yicha ANIQ moslash.
   │      Javobni KOD tuzadi, LLM emas — raqamlar to'qib chiqarilmasin.
   │
   ├─ 3b. TURKUM savoli ("kredit turlari", "Toshkent viloyatidagi filiallar")
   │      ->  katalogdan deterministik ro'yxat, LLM chaqirilmaydi.
   │
   └─ 3c. Qolgani  ->  RAG
          ├─ GIBRID QIDIRUV:
          │    • vektor qidiruv (Qdrant, cosine) — ma'noga yaqin bo'laklar
          │    • leksik qidiruv (IDF) — savoldagi so'zni matn ICHIDAN topadi
          │    natijalar navbat bilan birlashtiriladi
          ├─ prompt yig'iladi (kontekst + katalog + suhbat tarixi),
          │   hajmi qat'iy cheklangan — num_ctx dan oshmasligi uchun
          └─ Ollama (Qwen) javob yozadi -> kerak bo'lsa kirillga o'giriladi
```

Muhim tamoyil: **aniq ma'lumotni (raqam, IP, manzil, ro'yxat) kod beradi, modelga
faqat matnni gapga aylantirish topshiriladi.** Shuning uchun xodim ro'yxati yoki
mahsulot ro'yxati hech qachon to'liqsiz yoki uydirma bo'lmaydi.

---

## Texnologiyalar

**Backend**
- Python 3.13, FastAPI, Pydantic v2
- PostgreSQL 18 (SQLAlchemy 2.0 async, Alembic)
- Redis 7 (kesh, rate limiter, refresh-token rotatsiyasi)
- RabbitMQ + Celery (fon vazifalari: valyuta kurslarini yangilash, email, bildirishnomalar)
- Qdrant (vektor baza, RAG uchun)
- Ollama (LLM — `qwen3.5`; embedding — `mxbai-embed-large`)
- nginx (reverse proxy)
- JWT (access + refresh, rotatsiya va qayta ishlatishni aniqlash), Argon2
- Docker / Docker Compose

**Frontend**
- React 18 + TypeScript, Vite
- React Router 6, CSS Modules
- GSAP (animatsiya), react-icons / flag-icons
- Docker (ko'p bosqichli build -> `serve`)

---

## Arxitektura

Monorepo, ikkita mustaqil ilova.

```
turon-ai/
├── backend/                        # FastAPI modulli monolit
│   ├── Makefile                    # barcha ishga tushirish buyruqlari
│   ├── infra/
│   │   ├── docker-compose.yml      # asosiy stack (prod)
│   │   ├── docker-compose.override.yml   # dev (auto-reload, faqat lokal)
│   │   ├── docker/                 # Dockerfile, Dockerfile.dev
│   │   ├── nginx/                  # app.conf (prod), dev-nginx.conf
│   │   ├── postgres/               # Dockerfile + postgresql.conf
│   │   └── requirements/           # base/dev/prod .in va .txt
│   ├── migrations/                 # Alembic migratsiyalari (COMMIT QILINGAN)
│   ├── models/                     # ORM model reestri
│   ├── celery_tasks/               # Celery kirish nuqtasi
│   ├── scripts/                    # create_superadmin, check_employee, ...
│   ├── src/
│   │   ├── core/                   # UMUMIY infratuzilma
│   │   │   ├── ai/                 # Ollama klienti, embeddings, factory
│   │   │   ├── vectorstore/        # QdrantStore
│   │   │   ├── database/           # repository + Unit of Work
│   │   │   ├── redis/  limiter/  errors/  email_service/  http/  utils/
│   │   ├── user/                   # foydalanuvchilar + auth/
│   │   ├── chat/                   # chat sessiyalari, xabarlar, ovozlar
│   │   ├── knowledge/              # RAG YADROSI
│   │   │   ├── router.py           # savolni TUSHUNISH (intent)
│   │   │   ├── usecases.py         # qidiruv, katalog, xodim, javob yig'ish
│   │   │   ├── prompts.py          # system promptlar
│   │   │   ├── chunking.py         # matnni bo'laklarga bo'lish
│   │   │   ├── scraper.py          # sayt sahifasini parsing
│   │   │   ├── pdf_extractor.py    # PDF matn qatlami + OCR
│   │   │   ├── employee_parser.py  # Excel xodimlar ma'lumotnomasi
│   │   │   └── rates_scraper.py    # valyuta kurslari
│   │   ├── admin/                  # admin panel usecase'lari
│   │   ├── notifications/  reports/
│   │   ├── system/                 # health, time, AI diagnostika
│   │   └── main/                   # config.py, lifespan.py, presentation.py
│   └── tests/                      # pytest (unit/, factories/, fakes/)
└── frontend/
    ├── Dockerfile                  # build -> serve (3001-port)
    ├── docker-compose.yml
    └── src/
        ├── pages/                  # Login, Register, Chat, Admin, NotFound
        ├── components/             # admin/, chat/, common/, login/ + effektlar
        ├── services/               # API qatlami (authService, chatBot, admin...)
        ├── contexts/  hooks/  locales/  types/  utils/  constants/
```

**Backend qatlamlari:** `Repository -> UseCase -> Router`. Biznes mantiq router'da
turmaydi. Tranzaksiyalar Unit of Work orqali (`core/database/uow/`). Barcha biznes
yo'llari `/v1/...` prefiksida.

**Yangi modul qo'shish:** router'ni `src/main/presentation.py` da ro'yxatdan
o'tkazing, repozitoriyni UoW'ga qo'shing, ORM modelni `models/__init__.py` ga
yozing. To'liq tartib — `backend/README.md`.

---

## Tez boshlash

Talab: **Docker** va **Docker Compose**, frontend uchun **Node.js 20+**.

```bash
git clone <repo-url>
cd turon-ai
```

### 1. Backend

`.env` fayli git'ga kirmaydi — namunadan nusxa oling:

```bash
cd backend
cp .env.example .env
```

`.env` ichida to'ldirilishi shart bo'lganlar:

| O'zgaruvchi | Izoh |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | baza hisob ma'lumotlari |
| `POSTGRES_HOST` | **`postgres`** bo'lib qolsin — bu Docker servis nomi, `localhost` emas |
| `REDIS_PASSWORD`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | infratuzilma parollari |
| `JWT_*_SECRET_KEY` (4 ta) | tasodifiy uzun satrlar |
| `SUPER_ADMIN_USERNAME` / `_PASSWORD` / `_EMAIL` / `_PHONE` | birinchi admin |
| `OLLAMA_BASE_URL` | Ollama serverining manzili (masalan `http://10.0.0.5:11434`) |
| `OLLAMA_MODEL` | `qwen3.5:latest` |
| `EMBEDDING_MODEL` | `mxbai-embed-large:latest` |
| `QDRANT_HOST` / `QDRANT_PORT` | `qdrant` / `6333` |

`.env` to'liqligini tekshirish:

```bash
python scripts/check_env.py
```

Stack'ni ko'tarish:

```bash
make deploy-dev
```

> `deploy-dev` — dev rejim: kod o'zgarsa avtomatik qayta yuklanadi (uvicorn `--reload`),
> loyiha papkasi konteynerga ulanadi.
> Serverga chiqarish uchun: `make deploy-prod` (gunicorn, 4 worker).

Migratsiyalar allaqachon commit qilingan — toza clone'da ularni qayta generatsiya
qilish **shart emas**, `make deploy-dev` sxemani to'liq quradi.

Birinchi adminni yaratish:

```bash
make shell
```
```bash
python -m scripts.create_superadmin
```
```bash
exit
```

### 2. Frontend

```bash
cd frontend
npm install
```

`frontend/.env` faylini yarating:

```
VITE_API_URL=http://localhost:8100
```

> Diqqat: backend host mashinada **8100**-portda turadi (nginx orqali), 8000 da emas.

Dev serverni ishga tushirish:

```bash
npm run dev
```

Yoki Docker'da (ishlab chiqarish bundle'i):

```bash
docker compose up --build -d
```

> Docker image'da API manzili **build vaqtida** `docker-compose.yml` dagi
> `VITE_API_URL` build-arg orqali yoziladi. Uni o'zgartirsangiz image'ni qayta
> build qilish kerak.

---

## Portlar va manzillar

| Xizmat | Manzil | Izoh |
|---|---|---|
| Frontend (Vite dev) | http://localhost:5173 | `npm run dev` |
| Frontend (Docker) | http://localhost:3001 | faqat `127.0.0.1` ga bog'langan |
| Backend API | http://localhost:8100 | nginx -> app |
| Swagger | http://localhost:8100/docs | interaktiv API hujjati |
| Health-check | http://localhost:8100/health/ | |
| AI diagnostikasi | http://localhost:8100/diagnostic | Ollama bilan aloqa tekshiruvi |
| Qdrant dashboard | http://localhost:6333/dashboard | vektor bazani ko'rish |
| Qdrant REST/gRPC | 6333 / 6334 | |

PostgreSQL, Redis va RabbitMQ portlari **tashqariga chiqarilmagan** — ularga faqat
konteyner ichidan murojaat qilinadi (pastdagi buyruqlarga qarang).

API prefikslari:

| Prefiks | Nima |
|---|---|
| `/v1/users/...` | ro'yxatdan o'tish, kirish, token yangilash |
| `/v1/chat/...` | chat sessiyalari, xabarlar, `POST /v1/chat/ask` |
| `/v1/admin/...` | foydalanuvchilar CRUD, dashboard |
| `/v1/admin/knowledge/...` | bilim bazasi (yuklash, ro'yxat, o'chirish) |
| `/v1/notifications/...`, `/v1/reports/...` | bildirishnomalar, murojaatlar |
| `/health/`, `/time/`, `/diagnostic` | tizim (prefikssiz) |

---

## Kundalik buyruqlar

Hammasi `backend/` papkasidan bajariladi.

### Ishga tushirish / to'xtatish

| Buyruq | Nima qiladi |
|---|---|
| `make deploy-dev` | build + start (auto-reload) + migratsiya |
| `make deploy-prod` | build + down + up + migratsiya (gunicorn) |
| `make up` / `make down` | konteynerlarni yoqish / o'chirish |
| `make restart` | qayta ishga tushirish |
| `make info` | konteynerlar holati + barcha buyruqlar ro'yxati |

### Loglar

| Buyruq | Nima |
|---|---|
| `make logs-app` | backend loglari |
| `make logs-celery` | Celery worker |
| `make logs-postgres` | baza |
| `make logs` | hammasi |

### Migratsiyalar

Model o'zgargach migratsiyani **dev rejimda** yarating (shunda fayl host mashinaga
yoziladi) va uni **commit qiling**:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.override.yml exec app alembic revision --autogenerate -m "izoh"
```

So'ng qo'llang:

```bash
make migrate
```

> `make migration` buyrug'i `read -p` ishlatadi va **Windows'da ishlamaydi** — yuqoridagi
> to'liq buyruqdan foydalaning.

### Tozalash

| Buyruq | Nima qiladi | Ehtiyot |
|---|---|---|
| `make clean-resources` | ishlatilmayotgan Docker resurslarini o'chiradi | xavfsiz |
| `make clean` | konteyner + **volume**'larni o'chiradi | **barcha ma'lumot yo'qoladi** |
| `make clean-resources-hard` | barcha image va build keshni o'chiradi | keyingi build uzoq davom etadi |

---

## Admin bilan ishlash

Barcha skriptlar `app` konteyneri ichida bajariladi (`make shell` bilan kiring).

**Birinchi adminni yaratish** — `.env` dagi `SUPER_ADMIN_*` qiymatlari ishlatiladi.
Agar admin allaqachon bo'lsa, skript hech narsa qilmaydi:

```bash
python -m scripts.create_superadmin
```

**Admin parolini tiklash:**

```bash
python -m scripts.reset_admin_password
```
```bash
python -m scripts.reset_admin_password "YangiParol123!"
```

**Foydalanuvchini o'chirish / rolini o'zgartirish** — admin panelidan
(`/v1/admin/users/...` yoki frontend Admin sahifasi) bajariladi.

---

## Ma'lumotlar bazasi (PostgreSQL)

Baza porti tashqariga chiqarilmagan, shuning uchun `psql` konteyner ichida ishlaydi.
Quyidagi buyruqlar `backend/` dan bajariladi (`<USER>` va `<DB>` o'rniga `.env`
dagi `POSTGRES_USER` / `POSTGRES_DB` qiymatlarini qo'ying):

**Bazaga kirish:**

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec postgres psql -U <USER> -d <DB>
```

`psql` ichida foydali buyruqlar:

| Buyruq | Nima |
|---|---|
| `\dt` | jadvallar ro'yxati |
| `\d users` | `users` jadvali tuzilishi |
| `SELECT id, username, role FROM users;` | foydalanuvchilar |
| `SELECT version_num FROM alembic_version;` | joriy migratsiya |
| `\q` | chiqish |

**Bazaning holatini tez tekshirish:**

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec postgres psql -U <USER> -d <DB> -c "\dt"
```

**Zaxira nusxa olish:**

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec postgres pg_dump -U <USER> <DB> > backup.sql
```

**Bazani BUTUNLAY tozalash** (volume o'chadi, sxema noldan quriladi):

```bash
docker compose --env-file .env -f infra/docker-compose.yml down -v
```
```bash
make deploy-dev
```

> `down -v` **qaytarib bo'lmaydi** — Postgres, Redis va **Qdrant** ma'lumotlari
> birga o'chadi. Avval zaxira nusxa oling.

---

## Vektor baza (Qdrant)

Bilim bazasi (hujjat bo'laklari + xodimlar) shu yerda saqlanadi. Kolleksiya nomi —
`.env` dagi `QDRANT_COLLECTION` (odatda `knowledge`).

**Ko'rish:** http://localhost:6333/dashboard — bo'laklar, payload'lar va nuqtalar
soni ko'rinadi.

**Nuqtalar sonini bilish:**

```bash
curl http://localhost:6333/collections/knowledge
```

**Xodim ma'lumoti bazada bormi — diagnostika skripti** (`make shell` ichida):

```bash
python scripts/check_employee.py 2206
```
```bash
python scripts/check_employee.py Xamdamboyev
```
```bash
python scripts/check_employee.py
```

Skript kolleksiyadagi umumiy nuqtalar sonini, `doc_type=employee` yozuvlar sonini va
so'rov bo'yicha topilganlarni ko'rsatadi — muammo qidiruv mantig'idami yoki
ma'lumotning o'zi yo'qmi, shuni ajratib beradi.

**Faqat vektor bazani tozalash** (Postgres'ga tegmasdan):

```bash
curl -X DELETE http://localhost:6333/collections/knowledge
```

Keyin ma'lumotni admin panelidan qayta yuklash kerak.

---

## Bilim bazasini to'ldirish

Admin panelidagi "Ma'lumotlar" bo'limi orqali (yoki to'g'ridan-to'g'ri API bilan).
Barcha yo'llar admin huquqini talab qiladi.

| Endpoint | Nima |
|---|---|
| `POST /v1/admin/knowledge/upload` | qo'lda matn (sarlavha + matn) |
| `POST /v1/admin/knowledge/scrape` | sayt sahifasini URL bo'yicha yuklab, matnini ajratadi |
| `POST /v1/admin/knowledge/pdf` | PDF (skanerlangan sahifalar OCR orqali) — **sinxron, sekin** |
| `POST /v1/admin/knowledge/employees` | xodimlar ma'lumotnomasi (`.xlsx`) |
| `POST /v1/admin/knowledge/employees-json` | xodimlar (tayyor JSON ro'yxati) |
| `GET /v1/admin/knowledge` | yuklangan materiallar ro'yxati |
| `GET /v1/admin/knowledge/detail` | bitta materialning bo'laklari |
| `PUT /v1/admin/knowledge` | materialni tahrirlash (o'chirib qayta yozadi) |
| `DELETE /v1/admin/knowledge` | sarlavha bo'yicha o'chirish |
| `POST /v1/admin/knowledge/ask` | RAG'ni admin sifatida sinash |

Har yuklashda matn bo'laklarga bo'linadi, har bo'lak embedding'ga aylantiriladi va
sarlavha bilan birga Qdrant'ga yoziladi. Xodimlar fayli qayta yuklanganda o'sha
bo'limlarning eski yozuvlari almashtiriladi.

> PDF yuklash **sinxron** bajariladi: OCR va LLM tozalash ko'p sahifali hujjatda bir
> necha daqiqa olishi mumkin va so'rov proksi tomonidan uzilishi mumkin. Katta
> hujjatni bo'lib yuklash yoki matnini qo'lda `upload` orqali kiritish ishonchliroq.

---

## Testlar va kod sifati

```bash
make test
```
```bash
make test-cov
```
```bash
make lint
```

- **Ruff** — qator uzunligi 88, isort (`force-sort-within-sections`)
- **Mypy strict** — to'liq tip annotatsiyalari majburiy (migratsiyalar, testlar va
  skriptlar bundan mustasno)
- CI'da qo'shimcha: `gitleaks`, `bandit`, `pip-audit`

Yangi kod atrofdagi kod uslubiga mos bo'lsin: backend izohlari **inglizcha**,
frontend izohlari **o'zbekcha**.

---

## Muammolarni bartaraf etish

**`.env` topilmadi / ilova ko'tarilmayapti**
`backend/.env` mavjudligini va `python scripts/check_env.py` xato bermasligini
tekshiring.

**Bazaga tashqaridan (DBeaver, pgAdmin) ulanib bo'lmayapti**
Bu ataylab shunday: Postgres, Redis va RabbitMQ portlari host mashinaga
chiqarilmagan. Vaqtincha ulanish kerak bo'lsa `infra/docker-compose.yml` dagi
`postgres` servisiga `ports: ["5432:5432"]` qo'shing — lekin bu faylni **serverga
shu holda chiqarmang**. Bir martalik ish uchun `psql` ni konteyner ichida ishlatgan
ma'qul (yuqoriga qarang).

**Frontend backendni ko'rmayapti**
`VITE_API_URL` **8100** bo'lishi kerak (nginx), 8000 emas. Docker image uchun qiymat
build vaqtida yoziladi — o'zgartirsangiz qayta build qiling.

**Fayl yuklanmayapti (413)**
nginx `client_max_body_size` hozir **10 MB** (`infra/nginx/app.conf`). Kattaroq PDF
uchun uni oshirib, nginx'ni qayta ishga tushiring.

**Javob juda sekin (bir necha daqiqa)**
Ollama serverida modelning GPU'da ishlayotganini tekshiring:

```bash
ollama ps
```

`100% CPU` chiqsa — model GPU'ga sig'magan. Yechim: GPU/VRAM muammosini hal qilish
yoki `OLLAMA_MODEL` ni kichikroq modelga almashtirish.

**Javob o'rtasidan uzilib qolyapti**
Prompt `OLLAMA_NUM_CTX` (odatda 8192 token) dan oshib ketgan bo'lishi mumkin. Har
javobda backend log'ga prompt hajmini yozadi:

```bash
make logs-app
```

`Prompt: N belgi (~M token)` qatoriga qarang. `M` qiymati `num_ctx` ga yaqinlashsa,
`AnswerQuestionUseCase` dagi `MAX_CONTEXT_CHARS` / `MAX_CATALOG_CHARS` /
`MAX_HISTORY_CHARS` cheklovlarini pasaytiring yoki `OLLAMA_NUM_CTX` ni oshiring.

**AI umuman javob bermayapti**
http://localhost:8100/diagnostic — Ollama bilan aloqani tekshiradi. `ok: false`
bo'lsa `OLLAMA_BASE_URL` va tarmoqni tekshiring.

**pip build SSL xatosi bilan yiqilyapti (bank tarmog'i)**
Dockerfile'da `--trusted-host pypi.org --trusted-host files.pythonhosted.org`
ishlatilgan. Yangi paket qo'shsangiz shu yo'lni saqlang.
