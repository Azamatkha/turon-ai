# --- Build stage ---
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUSERBASE=/install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpq-dev \
    make \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY infra/requirements/prod.txt infra/requirements/base.txt ./requirements/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --user -r requirements/prod.txt

# --- Final stage ---
FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUSERBASE=/install \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.13/site-packages"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && mkdir -p /data /models \
    && chown appuser:appuser /app /data /models

# Turon AI OCR: yuqori sifatli (tessdata_best) til modellari (uzb/uzb_cyrl/rus)
RUN TESSDATA="$(find /usr/share -type d -name tessdata | head -n1)" \
    && wget -q -O "$TESSDATA/uzb.traineddata"      https://github.com/tesseract-ocr/tessdata_best/raw/main/uzb.traineddata \
    && wget -q -O "$TESSDATA/uzb_cyrl.traineddata" https://github.com/tesseract-ocr/tessdata_best/raw/main/uzb_cyrl.traineddata \
    && wget -q -O "$TESSDATA/rus.traineddata"      https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata

# bge-m3 modeli shu yerga (volume) bir marta yuklanadi
ENV HF_HOME=/models

COPY --from=builder --chown=appuser:appuser /install /install
COPY --chown=appuser:appuser . .

USER appuser
