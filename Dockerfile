# =============================================================================
# Accura – single-container image (frontend + API in one web service)
#
# Used by render.yaml. The Next.js server listens on $PORT (the only public
# port) and proxies /api/v1/* to the Sanic API on 127.0.0.1:8000 inside the
# same container: one URL, no CORS, no API address to configure.
#
#   docker build -t accura .
#   docker run -p 10000:10000 --env-file backend/.env accura
# =============================================================================

# ── Frontend build ───────────────────────────────────────────────────────────
FROM node:22-slim AS web-build
WORKDIR /src
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/
RUN npm ci --include=dev --no-audit --no-fund
COPY frontend/ frontend/
# Same-origin API: the browser calls /api/v1, Next forwards it to the API
ENV NEXT_OUTPUT=standalone \
    BACKEND_URL=http://127.0.0.1:8000 \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace frontend

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=10000

# Node runtime for the standalone Next server (no npm needed at runtime)
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends curl libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/

COPY --from=web-build /src/frontend/.next/standalone/ web/
COPY --from=web-build /src/frontend/.next/static web/frontend/.next/static
COPY --from=web-build /src/frontend/public web/frontend/public

COPY docker/start.sh /usr/local/bin/start-accura
RUN chmod +x /usr/local/bin/start-accura \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/v1/health" || exit 1

CMD ["start-accura"]
