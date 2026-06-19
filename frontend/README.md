# 🏦 Turon-AI

Bank ichki hujjatlari bo'yicha **savol-javob tizimi** (RAG).
Skanerlangan PDF hujjatlarni o'qiydi, ma'noga qarab qidiradi va (keyingi bosqichda)
AI yordamida savollarga javob beradi.

---

## 🧩 Texnologiyalar

| Qatlam | Vosita | Vazifasi |
|--------|--------|----------|
| OCR | Tesseract + Poppler | skanerlangan PDF → matn |
| Bo'lish | o'z kodimiz (`chunking.py`) | uzun matn → kichik bo'laklar |
| Embedding | `BAAI/bge-m3` | matn → 1024 o'lchamli vektor |
| Vector baza | **Qdrant** | vektorlarni saqlash va qidirish |
| API | FastAPI + Uvicorn | veb-server |
| Frontend | React + TypeScript + Vite | veb-interfeys (login, chat, admin) |
| Konteyner | Docker + Docker Compose | hammasini bir xil ishga tushirish |

---

## 🏛️ Arxitektura

```
A QISM — INGEST (bir martalik: PDF'larni bazaga yozish)
  ingest.py  →  ocr.py  →  chunking.py  →  embeddings.py  →  Qdrant

B QISM — SO'ROV (har safar: savolga javob)
  retriever.py  →  embeddings.py  →  Qdrant  →  [keyingi bosqich: AI]  →  main.py
```

### Fayllar vazifasi

| Fayl | Vazifasi |
|------|----------|
| `app/rag/ocr.py` | PDF rasmini tozalab matnga o'qiydi |
| `app/rag/chunking.py` | matnni bo'laklarga bo'ladi + hujjat mavzusini topadi |
| `app/rag/embeddings.py` | matnni vektorga aylantiradi |
| `app/rag/db.py` | Qdrant bazasiga ulanadi |
| `app/rag/ingest.py` | hammasini birlashtirib bazaga **yozadi** |
| `app/rag/retriever.py` | savolga o'xshash bo'laklarni **topadi** |
| `app/main.py` | veb-server (API) |

### Frontend (React + TypeScript + Vite)

Inline-style asosidagi dizayn, har sahifa mustaqil holat (state) bilan. Hozircha backendga ulanmagan.

| Fayl | Vazifasi |
|------|----------|
| `src/main.tsx` | kirish nuqtasi + marshrutlar (React Router) |
| `src/pages/LoginPage.tsx` | kirish sahifasi (uz/ru til, validatsiya, parol ko'rsatish) |
| `src/pages/ChatPage.tsx` | chat interfeysi |
| `src/pages/AdminPage.tsx` | admin paneli |
| `src/index.css` | global stillar + animatsiyalar (keyframes) |

Marshrutlar: `/login` → `/chat` → `/admin`.

---

## 🚀 Ishga tushirish

Talab: Docker + Docker Compose.

### Hammasini ko'tarish
```bash
docker compose up --build
```
| Xizmat | Manzil |
|--------|--------|
| Frontend (React) | http://localhost:5173 |
| Backend API (Swagger) | http://localhost:8000/docs |
| Qdrant panel | http://localhost:6333/dashboard |

Faqat bittasini ko'tarish: `docker compose up frontend` (yoki `backend`).

### Hujjatlarni bazaga yozish (ingest)
```bash
# 1) PDF'larni backend/data/documents/ ga tashla, keyin:
docker compose run --rm backend python -m app.rag.ingest
# 2) qidiruvni sinash:
docker compose run --rm backend python -m app.rag.retriever "savolingiz"
```
> Birinchi marta bge-m3 modeli (~2.3 GB) yuklanadi; `hf_models` volume'da saqlanadi, keyin tez.

Qayta ingest oldidan bazani tozalash:
```bash
docker compose run --rm backend python -c "from app.rag.db import client, COLLECTION; client.delete_collection(COLLECTION)"
```

### Frontend (alohida, Docker'siz)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Eslatmalar
- Kod (`.py`, `.tsx`) o'zgarsa **qayta build shart emas** — kod jonli ulangan (hot-reload).
- Faqat `Dockerfile` / `requirements.txt` / `package.json` o'zgarsa `docker compose build` kerak.
- Frontend bog'liqliklari o'zgarsa volume'ni yangilab ko'tar: `docker compose up -V frontend`.

---

## ⚙️ Sozlamalar

| Joy | O'zgaruvchi | Tavsif |
|-----|-------------|--------|
| `ocr.py` | `TILLAR` | OCR tillari (`uzb+rus`, kirill uchun `uzb_cyrl+rus`) |
| `ocr.py` | `DPI` | rasm sifati (400) |
| `chunking.py` | `bolak_olchami` | bo'lak hajmi (800 belgi) |
| `db.py` | `COLLECTION` | Qdrant kolleksiya nomi |
| `docker-compose.yml` | `QDRANT_HOST` | baza manzili (docker'da `qdrant`) |

---

## 📌 Holat (rivojlanish bosqichlari)

- [x] 1-bosqich: PDF OCR → bo'lish → vektor → Qdrant (AI'siz)
- [x] OCR sifatini oshirish (preprocessing + `tessdata_best`)
- [x] Har bo'lakka hujjat mavzusi (sarlavha)
- [x] Frontend: React+TS skeleti + Login sahifasi
- [ ] Frontend: Chat va Admin sahifalari
- [ ] 2-bosqich: AI (LLM) ulash — `/ask` endpoint
- [ ] Frontend ↔ backend ulash

---

## 📁 Papka tuzilishi

```
turon-ai/
├── docker-compose.yml      # qdrant + backend + frontend ni birga ishga tushiradi
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile          # backend obrazi (tesseract+python)
│   ├── .dockerignore
│   ├── requirements.txt    # python kutubxonalar
│   ├── data/documents/     # PDF'lar shu yerga
│   └── app/
│       ├── main.py         # FastAPI server
│       └── rag/            # RAG mantiq (ocr, chunking, embeddings, db, ingest, retriever)
└── frontend/
    ├── Dockerfile          # frontend obrazi (node + vite)
    ├── package.json
    ├── index.html
    └── src/
        ├── main.tsx        # router
        ├── index.css       # global stillar + animatsiyalar
        └── pages/          # LoginPage, ChatPage, AdminPage
```
