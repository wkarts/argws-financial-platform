FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates postgresql-client zstd rclone age tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY VERSION /app/VERSION
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./
COPY scripts/ /workspace/scripts/

# O runtime usa UID não-root estável. O GID 0 é intencional: os bind mounts
# preparados pelo financial-storage-init são root:root 0770. Assim o processo
# continua sem privilégios de root (UID 10001), mas consegue acessar os
# diretórios persistentes sem abrir permissões 0777 no host.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p \
        /data/backups \
        /data/runtime \
        /data/acme \
        /data/cloudpanel/domains \
        /var/lib/celery \
    && chown -R appuser:root /app /data /workspace /var/lib/celery \
    && chmod 0770 /data/backups /data/runtime /var/lib/celery

USER 10001:0
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
