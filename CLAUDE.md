# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Turon-AI is a RAG (retrieval-augmented generation) Q&A system over scanned bank-internal PDF documents (in Uzbek/Russian). Code, comments, and variable/function names throughout the codebase are written in Uzbek — keep new code consistent with this convention unless told otherwise.

Currently implemented: OCR ingest pipeline + vector search (no LLM answering yet — see Status below). The frontend (Login/Chat/Admin pages) exists but is not yet wired to the backend.

## Commands

The only required tool is Docker + Docker Compose; no local Python/Node/Tesseract install is needed.

```bash
docker compose up --build        # start qdrant + backend + frontend
docker compose up frontend       # start just one service (or `backend`)
docker compose up -d             # start in background
```

- Frontend: http://localhost:5173
- Backend API / Swagger docs: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

Code changes hot-reload (volumes are mounted) — no rebuild needed. Only rebuild (`docker compose build`) when `Dockerfile`, `requirements.txt`, or `package.json` changes. If frontend deps change, run `docker compose up -V frontend` to refresh the node_modules volume.

### RAG ingest / retrieval (run inside the backend container)

```bash
# put PDFs in backend/data/documents/, then:
docker compose run --rm backend python -m app.rag.ingest

# sanity-check vector search (no LLM involved yet):
docker compose run --rm backend python -m app.rag.retriever "savolingiz"

# wipe the Qdrant collection before re-ingesting:
docker compose run --rm backend python -c "from app.rag.db import client, COLLECTION; client.delete_collection(COLLECTION)"
```

The bge-m3 embedding model (~2.3GB) downloads once into the `hf_models` docker volume on first use.

### Frontend-only commands (if working outside Docker)

```bash
cd frontend
npm run dev       # vite dev server
npm run build     # tsc && vite build
npm run preview
```

## Architecture

Two pipelines share the same embedding model and Qdrant collection (`turon_docs`, 1024-dim cosine vectors):

```
INGEST (one-off, via CLI):  ingest.py → ocr.py → chunking.py → embeddings.py → Qdrant
QUERY (per request):        retriever.py → embeddings.py → Qdrant → [TODO: LLM] → main.py
```

`backend/app/rag/`:
- `ocr.py` — scanned PDFs have no text layer, only images. Converts each page to an image (poppler/pdf2image), preprocesses it (grayscale → autocontrast → median filter → Otsu binarization) to improve OCR accuracy, then runs pytesseract with `tessdata_best` language models (`uzb+rus`, configurable to `uzb_cyrl+rus` for Cyrillic docs).
- `chunking.py` — splits text into ~800-char chunks on sentence boundaries (never mid-word/mid-sentence), with 150-char overlap between consecutive chunks so context isn't lost at boundaries. Also extracts a document title (`sarlavha_aniqla`) from page 1 by locating Uzbek document-type keywords (nizom, qaror, yo'riqnoma, etc.) and taking a window of text around the match.
- `embeddings.py` — wraps `BAAI/bge-m3` via sentence-transformers; the model is lazy-loaded once into a module-level global and reused.
- `db.py` — Qdrant client and collection setup. Connects via `QDRANT_HOST`/`QDRANT_PORT` env vars (set to `qdrant` in docker-compose, defaults to `localhost` otherwise).
- `ingest.py` — one-time CLI script: reads every PDF in `data/documents/`, OCRs it, chunks it, prepends the detected title to each chunk before embedding (so retrieval is title-aware), and upserts into Qdrant with payload `{matn, sarlavha, manba, bolak}`.
- `retriever.py` — embeds a query and does a `top_k` similarity search against Qdrant. This is a pre-LLM sanity check, not a real answer endpoint.

`backend/app/main.py` — FastAPI app; currently only a health check at `/`. The planned `/ask` endpoint (retriever → LLM → answer) is not yet implemented.

`frontend/src/`:
- `main.tsx` — React Router setup; routes `/login` → `/chat` → `/admin`.
- `pages/LoginPage.tsx`, `ChatPage.tsx`, `AdminPage.tsx` — independent, self-contained state per page, inline-style based. Not yet connected to the backend.

## Status

- [x] Stage 1: PDF OCR → chunking → embedding → Qdrant (no AI)
- [x] OCR quality improvements (preprocessing + tessdata_best)
- [x] Per-chunk document title detection
- [x] Frontend pages (Login, Chat, Admin)
- [ ] Stage 2: wire up an LLM — `/ask` endpoint
- [ ] Connect frontend to backend
