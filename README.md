# Turon-AI

**Turonbank xodimlari uchun ichki AI yordamchi (chatbot).**

Xodim tizimga kiradi va bank mahsulotlari, ichki hujjatlar, filiallar hamda xodimlar
ma'lumotnomasi bo'yicha savol beradi. Javob bank o'zining ma'lumotlaridan olinadi —
bot hech narsani "o'ylab topmaydi".

Maqsad: xodim kerakli ma'lumotni qidirib o'tirmasin. Ilgari ~2000 ta ichki hujjat va
sayt sahifalari bo'ylab qo'lda qidirishga ketadigan vaqt savol-javobga aylanadi.

Chatdan tashqari **"Yordamchi dasturlar"** (mini-ilovalar) bor: valyuta kurslari,
kredit/ipoteka/omonat kalkulyatori, ichki raqamlar ma'lumotnomasi, hujjatlarni PDF'ga
aylantirish va muammo/taklif yuborish.

Ikki mijoz **bitta backend**dan foydalanadi: veb (React) va mobil ilova (Flutter).
Mobil ilova ro'yxatdan o'tish va Face-ID verifikatsiyasini ham bajaradi — vebda
`/register` yopilgan (login'ga yo'naltiriladi). Shu sabab har bir yangi funksiya
**API orqali** qilinadi va API hujjati (admin panel → API Docs) yangilab boriladi.

Interfeys uch tilda: **o'zbekcha (lotin)**, **o'zbekcha (kirill)**, **ruscha**.

---

## Mundarija

- [Qanday ishlaydi](#qanday-ishlaydi)
- [Yordamchi dasturlar (mini-ilovalar)](#yordamchi-dasturlar-mini-ilovalar)
- [Fon vazifalari va bildirishnomalar](#fon-vazifalari-va-bildirishnomalar)
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

## Yordamchi dasturlar (mini-ilovalar)

Chat sahifasining yuqori panelidagi **"Yordamchi dasturlar"** tugmasi (katakchali
ikonka) quti ochadi, ilovalar shu qutida turadi. Har biri — oddiy API, mobil ilova
ham aynan shu endpointlardan foydalanadi.

| Ilova | Endpoint | Izoh |
|---|---|---|
| Valyuta kurslari | `GET /v1/chat/rates` | Qdrant'dan o'qiladi, saytga bormaydi (pastda — [fon vazifalari](#fon-vazifalari-va-bildirishnomalar)) |
| Kalkulyator | `POST /v1/calculator/loan`, `/deposit` | kredit/ipoteka/omonat — sof formulalar, bazaga tegmaydi |
| To'lov jadvali | `POST /v1/calculator/schedule` (JSON), `/schedule/xlsx?lang=uz` (Excel fayl) | vebda Excel brauzerda yig'iladi, mobil tayyor faylni oladi |
| Ichki raqamlar | `GET /v1/users/directory/departments`, `GET /v1/users/directory?department=&q=` | bo'lim → xodim → **IP (ichki) raqam**. Faqat ism, lavozim, bo'lim, IP qaytadi — telefon/PNFL/pasport **qaytarilmaydi** |
| PDF'ga aylantirish | `POST /v1/tools/convert/to-pdf` (multipart, `files`) | bitta Word/Excel/PowerPoint yoki 1–20 ta rasm → bitta PDF. Jami 9 MB. Fayllar serverda saqlanmaydi |
| Muammo yoki taklif | `POST /v1/reports` | skrinshot bilan, adminga bildirishnoma boradi |

**Kalkulyatordagi `method`** kredit turiga bog'lanmagan — foydalanuvchi tanlaydi:
`flat` (ustama, har oy bir xil), `annuity` (teng to'lov), `diff` (differensial,
to'lov kamayib boradi). Yuborilmasa — `flat`.

**PDF konvertor** (`backend/src/tools/`): rasmlar `pymupdf` bilan (telefon rasmining
EXIF burilishi to'g'rilanadi, keng rasm — albom sahifa), hujjatlar backend image'iga
o'rnatilgan **LibreOffice** (`soffice --headless`) bilan o'giriladi. Bir vaqtda ko'pi
bilan 2 ta LibreOffice jarayoni, bitta hujjatga 120 soniya (`CONVERT_TIMEOUT_SECONDS`).
Skanerlangan PDF yoki parolli hujjat o'girilmaydi (400).

**Yangi mini-ilova qo'shish:** backend'da endpoint (`routers.py` → `usecases.py`,
`presentation.py` ga ro'yxatdan o'tkazish) → apiDocs'ni yangilash → frontend'da
`src/services/` ga servis, modal komponent va `ChatHeader.tsx` dagi `miniApps`
ro'yxatiga bitta yozuv. Matnlar uchala tilga (`src/locales/*/chat.ts`).

Mobil dasturchi uchun qo'llanmalar: [`docs/mobile/`](docs/mobile/) (masalan
[ichki raqamlar](docs/mobile/ichki-raqamlar.md) — API, ekran oqimi, Flutter kodi).

---

## Fon vazifalari va bildirishnomalar

Celery beat jadvali (`backend/celery_tasks/main.py`, vaqtlar UTC):

| Vazifa | Qachon | Nima qiladi |
|---|---|---|
| `scrape_exchange_rates` | har kuni 06:00 UTC (**11:00 Toshkent**) | turonbank.uz kurslar sahifasini o'qib, Qdrant'ga `title="Valyuta kurslari"` + strukturali `rates_json` bilan yozadi |
| `cleanup_unverified_users` | har daqiqa | ro'yxatdan o'tganiga 24 soat bo'lgan tasdiqlanmagan akkauntlarni o'chiradi |
| `cleanup_old_notifications` | har kuni 03:30 UTC | eskirgan bildirishnomalarni tozalaydi |

**Valyuta kurslari** faqat shu vazifa orqali yangilanadi. Admin paneldan kurslar
sahifasini havola sifatida qo'shish **kurs oynasini to'ldirmaydi** (u oddiy matn
bo'lib yoziladi, `rates_json` bo'lmaydi) va keyinchalik botga eski kursni aytdiradi —
bunday qilmang. Yangi kurs **avval yoziladi, keyin** eskisining ortiqcha bo'laklari
o'chiriladi: embedding/Qdrant yiqilsa ham kechagi kurs joyida qoladi.

Kursni qo'lda (11:00 ni kutmasdan) yangilash — `backend/` dan:

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec celery_worker python -m celery -A celery_tasks.main call scrape_exchange_rates
```

**Bildirishnomalar** — kimga boradi:

| Tur | Kimga | Qachon |
|---|---|---|
| `rates_updated` | hammaga | kuniga ko'pi bilan 1 marta, faqat kurs haqiqatan o'zgarganda |
| `knowledge_updated` | **faqat adminlarga** | bilim bazasiga ma'lumot qo'shilganda/tahrirlanganda |
| `report_new` | faqat adminlarga | har yangi murojaat |

`knowledge_updated` **birlashtiriladi**: 10 daqiqa ichida ketma-ket qo'shilgan
ma'lumotlar yangi qator emas, o'sha o'qilmagan qatorga qo'shiladi (`params.count`).
120 ta ma'lumot birdan qo'shilsa ham adminga bitta "…va yana 119 ta" keladi.

---

## Texnologiyalar

**Backend**
- Python 3.13, FastAPI, Pydantic v2
- PostgreSQL 18 (SQLAlchemy 2.0 async, Alembic)
- Redis 7 (kesh, rate limiter, refresh-token rotatsiyasi)
- RabbitMQ + Celery (fon vazifalari: valyuta kurslarini yangilash, email, bildirishnomalar)
- Qdrant (vektor baza, RAG uchun)
- Ollama (LLM — `qwen3.5`; embedding — `bge-m3:567m`, 1024 o'lcham) — alohida
  serverda, backend unga `OLLAMA_BASE_URL` orqali boradi
- LibreOffice (headless) + `pymupdf` / Pillow — PDF konvertor; Tesseract — PDF OCR
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
│   │   ├── admin/                  # admin panel usecase'lari (dashboard statistikasi)
│   │   ├── calculator/             # kredit/omonat formulalari + to'lov jadvali (.xlsx)
│   │   ├── tools/                  # mini-ilovalar: PDF konvertor (LibreOffice)
│   │   ├── notifications/  reports/
│   │   ├── system/                 # health, time, AI diagnostika
│   │   └── main/                   # config.py, lifespan.py, presentation.py
│   └── tests/                      # pytest (unit/, factories/, fakes/)
├── docs/
│   └── mobile/                     # mobil (Flutter) dasturchi uchun qo'llanmalar
└── frontend/
    ├── Dockerfile                  # build -> serve (3001-port)
    ├── docker-compose.yml
    └── src/
        ├── pages/                  # Login, Chat, Admin, Unverified, NotFound
        │                           # (/register yopilgan — ro'yxatdan o'tish mobilda)
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
| `EMBEDDING_MODEL` | `bge-m3:567m` — **Qdrant'dagi vektorlar shu model bilan yozilgan**, boshqasiga almashtirilsa bazani qayta yuklash kerak |
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
| `/v1/users/...` | kirish, token yangilash, profil, foydalanuvchilar CRUD, `directory` (ichki raqamlar) |
| `/v1/users/auth/...` | login/logout/refresh; mobil: register + Face-ID `save` |
| `/v1/chat/...` | chat sessiyalari, xabarlar, `POST /v1/chat/ask`, `GET /v1/chat/rates` |
| `/v1/calculator/...` | kredit/omonat hisobi, to'lov jadvali (JSON va `.xlsx`) |
| `/v1/tools/...` | mini-ilovalar: `convert/to-pdf` |
| `/v1/admin/...` | dashboard statistikasi |
| `/v1/admin/knowledge/...` | bilim bazasi (yuklash, ro'yxat, o'chirish) |
| `/v1/notifications/...`, `/v1/reports/...` | bildirishnomalar, murojaatlar |
| `/health/`, `/time/`, `/diagnostic` | tizim (prefikssiz) |

To'liq, namunali API hujjati — **admin panel → API Docs** (mobil dasturchi shundan
foydalanadi). Yangi endpoint qo'shilsa yoki o'zgarsa, `frontend/src/components/admin/apiDocs.html`
ham yangilanadi.

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
| `make logs-celery-beat` | Celery beat (jadval) |
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

**Foydalanuvchini o'chirish / rolini o'zgartirish / qo'lda tasdiqlash** — admin
panelidagi "Foydalanuvchilar" sahifasidan (ro'yxat 10 tadan sahifalangan) yoki API
orqali: `GET/POST /v1/users`, `PATCH/DELETE /v1/users/{user_id}`.

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

Yangi kod atrofdagi kod uslubiga mos bo'lsin: kod izohlari **o'zbekcha**.
Foydalanuvchiga ko'rinadigan har bir matn frontend'da uchala tilga
(`src/locales/{uz,uz_cyrl,ru}/`) qo'shiladi.

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
uchun uni oshirib, nginx'ni qayta ishga tushiring. PDF konvertorning o'z chegarasi —
jami **9 MB** (`CONVERT_MAX_BYTES`), multipart ustamasi 10 MB ga sig'ishi uchun.

**Valyuta kurslari oynasi bo'sh ("Hozircha kurs ma'lumoti yo'q")**
`GET /v1/chat/rates` xatosiz, lekin bo'sh qaytsa — Qdrant'da kurs yozuvi yo'q.
1. Worker logidan sababini toping:
   ```bash
   docker compose --env-file .env -f infra/docker-compose.yml logs --since 72h celery_worker | grep -iE "exchange_rates|kurs|Embedding|Qdrant"
   ```
   - `Embedding xizmati bilan bog'lanib bo'lmadi` — Ollama (embedding) ishlamayapti;
   - `sahifa tuzilishi o'zgargan` — turonbank.uz sahifasi o'zgargan, `rates_scraper.py` ni moslash kerak.
2. Sababni tuzatib, kursni [qo'lda yangilang](#fon-vazifalari-va-bildirishnomalar).
3. Qdrant'da kurs bormi:
   ```bash
   curl -s -X POST http://127.0.0.1:6333/collections/knowledge/points/count -H 'Content-Type: application/json' -d '{"filter":{"must":[{"key":"title","match":{"value":"Valyuta kurslari"}}]},"exact":true}'
   ```

**`.env` o'zgartirildi, lekin Celery eski qiymat bilan ishlayapti**
Konteyner `.env` ni faqat **yaratilganda** o'qiydi. App qayta ishga tushsa ham
`celery_worker`/`celery_beat` eski qiymatda qoladi (masalan `OLLAMA_BASE_URL`
almashtirilganda fon vazifalari eski serverga urilaveradi). Qayta yarating:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --force-recreate celery_worker celery_beat
```

Tekshirish:

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec celery_worker printenv OLLAMA_BASE_URL
```

**Ollama (embedding) serveri almashtirildi**
Yangi serverda ham aynan `bge-m3:567m` bo'lishi shart (`ollama list`). Boshqa model
bo'lsa: o'lcham farq qilsa Qdrant yozishni rad etadi, o'lcham bir xil bo'lsa ham
qidiruv noto'g'ri bo'laklarni topa boshlaydi — butun bilim bazasini qayta yuklash
kerak bo'ladi.

**PDF konvertor: "Konvertor (LibreOffice) serverda o'rnatilmagan" (500)**
Image eski — LibreOffice `infra/docker/Dockerfile` ga keyinroq qo'shilgan. Backend
image'ini qayta build qiling. Lokal (Docker'siz) muhitda faqat rasm → PDF ishlaydi.

**Javob juda sekin (bir necha daqiqa)**
Ollama serverida modelning GPU'da ishlayotganini tekshiring:

```bash
ollama ps
```

`100% CPU` chiqsa — model GPU'ga sig'magan. Yechim: GPU/VRAM muammosini hal qilish
yoki `OLLAMA_MODEL` ni kichikroq modelga almashtirish.

**Javob o'rtasidan uzilib qolyapti**
Prompt `OLLAMA_NUM_CTX` (hozir 16384 token) dan oshib ketgan bo'lishi mumkin. Har
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
