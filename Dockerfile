# ─── Stage 1 : Build ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système (WeasyPrint nécessite pango, cairo, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# ─── Stage 2 : Runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=kharandi_backend.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python installés depuis le builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Dossiers statiques, média et état du planificateur Celery Beat
RUN mkdir -p staticfiles media beat
RUN chmod +x start.sh start-worker.sh start-beat.sh beat-healthcheck.py

ENV PORT=8000
EXPOSE 8000

# Le démarrage (attente DB, migrations idempotentes, seed une-fois-seulement,
# collectstatic, gunicorn) est centralisé dans start.sh — une source de vérité.
# Le worker Celery utilise start-worker.sh (service `worker` de compose).
# Celery Beat utilise start-beat.sh (service `beat` de compose).
CMD ["bash", "start.sh"]
