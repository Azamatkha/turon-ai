# --- Build stage ---
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUSERBASE=/install

# --- LOCAL ONLY: behind the corporate proxy, which refuses excess parallel
# connections. Comment out this RUN when building on the server. ---
RUN printf 'Acquire::Queue-Mode "access";\nAcquire::Retries "10";\nAcquire::http::Pipeline-Depth "0";\n' \
      > /etc/apt/apt.conf.d/99-proxy-tuning
# --- end LOCAL ONLY ---

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpq-dev \
    make \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY infra/requirements/prod.txt infra/requirements/base.txt ./requirements/
RUN pip install --upgrade pip \
      --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    && pip install --no-cache-dir --user \
      --trusted-host pypi.org --trusted-host files.pythonhosted.org \
      -r requirements/prod.txt
# --- Final stage ---
FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUSERBASE=/install \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.13/site-packages"

# --- LOCAL ONLY: behind the corporate proxy, which refuses excess parallel
# connections. Comment out this RUN when building on the server. ---
RUN printf 'Acquire::Queue-Mode "access";\nAcquire::Retries "10";\nAcquire::http::Pipeline-Depth "0";\n' \
      > /etc/apt/apt.conf.d/99-proxy-tuning
# --- end LOCAL ONLY ---

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && mkdir -p /data \
    && chown appuser:appuser /app /data

COPY --from=builder --chown=appuser:appuser /install /install
COPY --chown=appuser:appuser . .

USER appuser
