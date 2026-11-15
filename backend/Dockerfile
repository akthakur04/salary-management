# The API image, built by Render (render.yaml) and by docker-compose.yml.
# On start it applies database migrations, then serves the API on $PORT.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

# Dependencies first, so code changes don't reinstall them. pip's downloads
# live in a build cache, outside the image: a build that fails part-way
# (say, a network timeout) resumes from what it already fetched.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir app && touch app/__init__.py && pip install . && rm -rf app build *.egg-info

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts/start.sh ./scripts/start.sh
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps . && rm -rf build *.egg-info

RUN useradd --create-home --uid 10001 api
USER api

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/health')"

CMD ["sh", "scripts/start.sh"]
