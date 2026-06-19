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

---

## 🚀 Ishga tushirish (BOSHIDAN OXIRIGACHA)

> ⚠️ Buyruqlarni **PowerShell**da ishlatish tavsiya etiladi (Windows Start → "PowerShell").
> Avval har doim `cd C:\projects\turon-ai` qil.

### 0-qadam: BIR MARTALIK sozlash (faqat birinchi marta)

**a) `.wslconfig` yarat** — WSL juda ko'p RAM yeb kompyuterni qotirib qo'ymasligi uchun.
PowerShell:
```powershell
notepad $env:USERPROFILE\.wslconfig
```
Ichiga yozib saqla:
```
[wsl2]
memory=6GB
processors=4
swap=8GB
```
Keyin:
```powershell
wsl --shutdown
```
Docker Desktop'ni qayta och.

### 1-qadam: Docker ishga tushganini tekshir
Docker Desktop ochiq va pastda **yashil "Engine running"** bo'lsin. Keyin:
```powershell
docker ps
```
Jadval (bo'sh bo'lsa ham) chiqsa — Docker tayyor.

### 2-qadam: Loyihani qurish (build)
```powershell
cd C:\projects\turon-ai
docker compose build
```
> Birinchi marta uzoq (tesseract + til modellari yuklanadi). Keyin tez (kesh).
> **Maslahat:** build paytida VS Code va brauzerni yop (RAM bo'sh bo'lsin).

### 3-qadam: Serverni ko'tarish
```powershell
docker compose up
```
Tekshir (brauzerda):
- API Swagger:    http://localhost:8000/docs
- Qdrant panel:   http://localhost:6333/dashboard

> To'xtatish: terminalda **Ctrl+C**. Yoki orqa fonda ishlatish: `docker compose up -d`

### 4-qadam: PDF qo'shish
PDF fayllarni shu papkaga tashla:
```
backend\data\documents\
```

### 5-qadam: Hujjatlarni bazaga yozish (ingest)
```powershell
docker compose run --rm backend python -m app.rag.ingest
```
> Birinchi marta bge-m3 modeli (~2.3 GB) yuklanadi — sekin. Keyin tez (volume'da saqlanadi).

### 6-qadam: Qidiruvni sinash
```powershell
docker compose run --rm backend python -m app.rag.retriever "savolingiz"
```

### Bazani tozalash (kodni o'zgartirib QAYTA ingest qilishdan oldin)
```powershell
docker compose run --rm backend python -c "from app.rag.db import client, COLLECTION; client.delete_collection(COLLECTION)"
```
Keyin yana 5-qadam (ingest).

---

## 🔁 Har kungi ish (qisqacha)

```powershell
cd C:\projects\turon-ai
docker compose up          # serverni ko'tar
# yangi PDF qo'shsang -> bazani tozalab, qayta ingest:
docker compose run --rm backend python -m app.rag.ingest
```

Kodni (`.py` fayllarni) o'zgartirsang **qayta build SHART EMAS** — `./backend` jonli ulangan.
Faqat `Dockerfile` yoki `requirements.txt` o'zgarsa `docker compose build` kerak.

---

## 🆘 Muammolar va yechimlari (biz duch kelganlar)

| Xato / holat | Sabab | Yechim |
|--------------|-------|--------|
| `daemon is running?` / `docker.sock ... no such file` | Docker Engine ishlamayapti | Docker Desktop'ni och, yashil "Engine running" kut |
| `500 Internal Server Error ... _ping` | Engine build paytida qulаdi (RAM) | `wsl --shutdown` → Docker Desktop qayta och → `.wslconfig` borligini tekshir |
| `Starting the Docker Engine...` da osilib qoladi | WSL backend muammosi | `wsl --shutdown` + `wsl --update` → Docker qayta och |
| Kompyuter qotib qoladi, RAM to'la (`VmmemWSL`) | WSL hamma RAMni yegan | `.wslconfig` yarat (0-qadam), `wsl --shutdown` |
| `command 'docker' could not be found in WSL` | WSL integration o'chiq | Docker Desktop → Settings → Resources → WSL Integration → yoq |
| `dockerfile parse error: unknown instruction` | `\` dan keyin `#` izoh qo'yilgan | Dockerfile'da izohni faqat alohida qatorga yoz |
| `'QdrantClient' object has no attribute 'search'` | yangi qdrant-client | `.search()` o'rniga `.query_points(...).points` |
| Model har safar 2.3 GB qayta yuklanadi | HF kesh saqlanmagan | `docker-compose.yml`da `hf_models:/models` volume borligini tekshir |

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
- [ ] 2-bosqich: AI (LLM) ulash — `/ask` endpoint
- [ ] 3-bosqich: frontend (chat interfeysi)

---

## 📁 Papka tuzilishi

```
turon-ai/
├── docker-compose.yml      # 2 xizmatni birga ishga tushiradi
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
└── frontend/               # veb-sahifalar (login, chat, admin)
```
