#!/usr/bin/env bash
# EmpowerHer: one-command setup and run (macOS / Linux).
#
#   ./setup.sh             set up everything and start the app
#   ./setup.sh --test      also run the automated tests before starting
#   ./setup.sh --no-run    set up only, do not start the server
#   ./setup.sh --no-demo   do not create the demo account
#   PORT=8080 ./setup.sh   use another port (default 8000)
#
# Safe to run again: existing keys, data and packages are kept.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/empowerher/backend"
VENV="$ROOT/.venv"
PORT="${PORT:-8000}"
RUN=1; TEST=0; DEMO=1

for arg in "$@"; do
    case "$arg" in
        --no-run) RUN=0 ;;
        --test) TEST=1 ;;
        --no-demo) DEMO=0 ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

step() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }

step "1/7 Finding Python 3.11 - 3.13"
PYTHON=""
for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(not (3, 11) <= sys.version_info[:2] <= (3, 13))'; then
        PYTHON="$(command -v "$candidate")"; break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Python 3.11, 3.12 or 3.13 is required. Install it from https://www.python.org/downloads/"
    exit 1
fi
echo "Using $("$PYTHON" --version) at $PYTHON"

step "2/7 Creating the virtual environment (.venv)"
if [ ! -x "$VENV/bin/python" ]; then
    "$PYTHON" -m venv "$VENV"
else
    echo "Already exists."
fi
PY="$VENV/bin/python"

step "3/7 Installing packages (first run takes a few minutes)"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r "$BACKEND/requirements.txt"
echo "Packages installed."

step "4/7 Creating backend/.env with new encryption keys"
cd "$BACKEND"
if [ -f .env ]; then
    echo ".env already exists; keeping your keys."
else
    "$PY" - <<'PYEOF'
import secrets
from cryptography.fernet import Fernet

with open(".env", "w") as env:
    env.write(f"""DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
IDEA_VAULT_ENCRYPTION_KEY={Fernet.generate_key().decode()}
# Encrypts uploaded documents (separate from the Idea Vault key).
DOCUMENT_ENCRYPTION_KEY={Fernet.generate_key().decode()}
# Optional: enables AI recommendations and the AI assistant.
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
""")
PYEOF
    echo "Created .env. Back it up: without these keys encrypted data cannot be read."
fi

step "5/7 Preparing datasets and database"
if [ ! -f datasets/processed/districts.csv ] || [ ! -f datasets/processed/states.csv ]; then
    "$PY" datasets/build_datasets.py
else
    echo "Processed datasets present."
fi
"$PY" manage.py migrate --noinput -v 0
echo "Database ready."

step "6/7 Demo account and tests"
if [ "$DEMO" = 1 ]; then
    "$PY" manage.py seed_demo | grep -v "witness" || true
fi
if [ "$TEST" = 1 ]; then
    "$PY" manage.py test
fi

if [ "$RUN" = 0 ]; then
    printf '\nSetup complete. Start the app with: ./setup.sh\n'
    exit 0
fi

step "7/7 Starting EmpowerHer at http://localhost:$PORT (Ctrl+C to stop)"
URL="http://localhost:$PORT/"
( sleep 3
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
  fi ) &
exec "$PY" manage.py runserver "127.0.0.1:$PORT"
