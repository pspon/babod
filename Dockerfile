# Multi-arch base: builds on x86 laptops and on arm64 Raspberry Pi OS alike.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BABOD_DB_PATH=/data/babod.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# uid 1000 matches the default `pi` user, so the bind-mounted ./data directory
# is writable without loosening permissions on the host.
RUN useradd --create-home --uid 1000 babod \
    && mkdir -p /data \
    && chown -R babod:babod /data /app
USER babod

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
