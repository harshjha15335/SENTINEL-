# Single-container SENTINEL: FastAPI serves the API and the built web app on one origin.
#   docker build -t sentinel .
#   docker run -p 8000:8000 -e SENTINEL_DATABASE_URL=... -e SENTINEL_PAYPAL_MODE=fixture sentinel

FROM node:24-slim AS web
WORKDIR /src
COPY packages/contracts ./packages/contracts
COPY apps/web/package.json apps/web/package-lock.json ./apps/web/
RUN --mount=type=secret,id=build_ca \
    cd apps/web && if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi && npm ci --no-audit --no-fund
COPY apps/web ./apps/web
RUN cd apps/web && npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    SENTINEL_WEB_DIST=/app/web SENTINEL_STORAGE_BACKEND=database HOST=0.0.0.0
WORKDIR /app
# Assemble the runtime in one filesystem layer. This avoids repeated copies of the
# Python dependency tree on VFS builders while keeping source mounts read-only.
RUN --mount=type=bind,source=apps/api,target=/source,readonly \
    --mount=type=bind,from=web,source=/src/apps/web/dist,target=/web-dist,readonly \
    --mount=type=secret,id=build_ca \
    set -eu; \
    cp /source/pyproject.toml ./; \
    cp -r /source/app ./app; \
    cp -r /source/alembic ./alembic; \
    cp /source/alembic.ini ./; \
    cp /source/scripts/start.sh ./start.sh; \
    cp -r /web-dist ./web; \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install .; \
    useradd --create-home --uid 10001 sentinel; \
    chmod -R a+rX /app; chmod 755 /app/start.sh
USER sentinel
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/v1/ready',timeout=4)"
CMD ["./start.sh"]
