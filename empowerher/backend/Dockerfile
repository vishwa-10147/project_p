# EmpowerHer: production-style image (gunicorn + WhiteNoise).
# Used by docker-compose.yml at the project root:  docker compose up --build

FROM python:3.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OpenCV (used by RapidOCR) needs these system libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install packages first so code changes don't re-download them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. /app/data holds the generated keys and the
# rate-limit cache, and is a Docker volume so it survives restarts.
RUN useradd --create-home --uid 1000 empowerher \
    && mkdir -p /app/data /app/staticfiles /app/media \
    && chown -R empowerher:empowerher /app/data /app/staticfiles /app/media \
    && chmod +x docker-entrypoint.sh
USER empowerher

ENV DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_DEBUG=False \
    DJANGO_CACHE_DIR=/app/data/cache \
    EMPOWERHER_KEYS_FILE=/app/data/keys.env \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT','8000'), timeout=4)" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WORKERS:-3} --timeout 60 --access-logfile - --error-logfile -"]
