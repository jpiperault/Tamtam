# syntax=docker/dockerfile:1
# --- 1. Interface web (JS/CSS statiques)
FROM --platform=$BUILDPLATFORM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- 2. Dépendances Python dans un venv
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
COPY server/requirements.txt /tmp/requirements.txt
RUN /venv/bin/pip install -r /tmp/requirements.txt && /venv/bin/pip uninstall -y pip

# --- 3. Image finale
FROM python:3.12-slim
ENV PATH=/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/server \
    WEB_DIST=/app/web/dist \
    PORT=8080
COPY --from=deps /venv /venv
COPY server/tamtam /app/server/tamtam
COPY docs/guide.md /app/server/tamtam/seed_docs/guide.md
COPY --from=web /web/dist /app/web/dist
# Hangar monte /data (seul dossier persistant) et l'attribue à cet utilisateur à chaque déploiement.
# pip ne sert pas à l'exécution : on le retire de l'image finale (moins de code exposé).
RUN mkdir -p /data && chown 10001:10001 /data \
    && python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true
USER 10001:10001
WORKDIR /app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"
CMD ["python", "-m", "tamtam"]
