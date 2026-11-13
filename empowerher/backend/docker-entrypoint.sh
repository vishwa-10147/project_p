#!/bin/sh
# Prepares the container, then runs the command (gunicorn by default).
set -eu

KEYS_FILE=/app/data/keys.env

# 1. Secret and encryption keys.
#    Use the ones passed in the environment if any; otherwise create them
#    once and keep them in the data volume. Losing them makes encrypted
#    ideas and documents unreadable, so back up the volume (see SETUP.md).
if [ ! -f "$KEYS_FILE" ]; then
    echo "==> First start: generating secret and encryption keys in $KEYS_FILE"
    python - "$KEYS_FILE" <<'EOF'
import os, secrets, sys
from cryptography.fernet import Fernet
path = sys.argv[1]
with open(path, "w") as f:
    f.write(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}\n")
    f.write(f"IDEA_VAULT_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n")
    f.write(f"DOCUMENT_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n")
os.chmod(path, 0o600)
EOF
fi
for line in $(cat "$KEYS_FILE"); do
    name=${line%%=*}
    # Values given in the environment win over the generated ones.
    eval "current=\${$name:-}"
    if [ -z "$current" ]; then
        export "$line"
    fi
done

# 2. Wait for the database (PostgreSQL may still be starting).
python - <<'EOF'
import sys, time
import django
django.setup()
from django.db import connection
for attempt in range(30):
    try:
        connection.ensure_connection()
        break
    except Exception as exc:  # noqa: BLE001
        print(f"==> Waiting for the database ({exc.__class__.__name__})")
        time.sleep(2)
else:
    sys.exit("Database not reachable.")
EOF

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput -v 0

if [ "${SEED_DEMO:-False}" = "True" ]; then
    echo "==> Creating the demo account"
    python manage.py seed_demo | grep -v "witness" || true
fi

exec "$@"
