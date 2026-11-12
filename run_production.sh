#!/usr/bin/env bash
# EmpowerHer: run in production mode with gunicorn (Linux / macOS).
#
# 1. Run ./setup.sh --no-run once (installs packages, creates .env).
# 2. Edit empowerher/backend/.env using .env.production.example as a guide
#    (DJANGO_DEBUG=False, your domain, a strong secret key).
# 3. ./run_production.sh        (PORT=8000 and WORKERS=3 by default)
#
# Put a TLS-terminating reverse proxy (nginx, Caddy, or your host's) in
# front of gunicorn and set DJANGO_BEHIND_PROXY=True.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/empowerher/backend"
PY="$ROOT/.venv/bin/python"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-3}"

if [ ! -x "$PY" ]; then
    echo "Run ./setup.sh --no-run first."; exit 1
fi
cd "$BACKEND"

if ! grep -qiE '^DJANGO_DEBUG=(false|0|no|off)' .env 2>/dev/null &&
   [ "${DJANGO_DEBUG:-}" != "False" ]; then
    echo "DJANGO_DEBUG is not False in empowerher/backend/.env."
    echo "See .env.production.example before running in production."
    exit 1
fi

echo "==> Checking the production configuration"
"$PY" manage.py check --deploy --fail-level WARNING

echo "==> Applying database migrations"
"$PY" manage.py migrate --noinput

echo "==> Collecting static files"
"$PY" manage.py collectstatic --noinput -v 0

echo "==> Starting gunicorn on port $PORT with $WORKERS workers"
exec "$ROOT/.venv/bin/gunicorn" config.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers "$WORKERS" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
