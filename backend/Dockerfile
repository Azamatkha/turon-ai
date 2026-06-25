# Backend "retsept"i: tesseract + poppler + python avtomatik o'rnatiladi.
# Lokal ham, server ham bir xil ishlaydi -- .exe ni qo'lda o'rnatish KERAK EMAS.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

# OCR tizim dasturlari va xavfsizlik sertifikatlari
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Yuqori sifatli (tessdata_best) til modellari -- OCR aniqligi sezilarli oshadi.
# apt'dagi oddiy modellar o'rniga shularni ishlatamiz.
RUN cd /usr/share/tesseract-ocr/5/tessdata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/uzb.traineddata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/uzb_cyrl.traineddata && \
    wget -q https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata

WORKDIR /app

# Avval kutubxonalar (kesh tezroq bo'lishi uchun alohida qadam)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Keyin kod
COPY . .

EXPOSE 8000

# Server salomatligini tekshirish (orkestratorlar uchun foydali)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
