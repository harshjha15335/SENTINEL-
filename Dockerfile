# Single-container SENTINEL: FastAPI serves the API and the built web app on one origin.
#   docker build -t sentinel .
#   docker run -p 8000:8000 -e SENTINEL_DATABASE_URL=... -e SENTINEL_PAYPAL_MODE=fixture sentinel

FROM node:24-slim AS web
WORKDIR /src
COPY packages/contracts ./packages/contracts
COPY apps/web/package.json apps/web/package-lock.json ./apps/web/
RUN cd apps/web && npm ci --no-audit --no-fund
COPY apps/web ./apps/web
RUN cd apps/web && npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    SENTINEL_WEB_DIST=/app/web
WORKDIR /app
COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
RUN pip install . && useradd --create-home --uid 10001 sentinel
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./
COPY apps/api/scripts/start.sh ./start.sh
COPY --from=web /src/apps/web/dist ./web
USER sentinel
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health',timeout=4)"
CMD ["./start.sh"]
