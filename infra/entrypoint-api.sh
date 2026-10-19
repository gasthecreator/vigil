#!/bin/sh
set -eu
# Refuse to start with unreplaced template placeholders (infra/.env.compose.example).
for v in DATABASE_URL JWT_SECRET_KEY VIGIL_FIELD_ENCRYPTION_KEYS; do
  eval "val=\${$v:-}"
  case "$val" in
    *REPLACE_ME*) echo "refusing to start: $v still contains a REPLACE_ME placeholder" >&2; exit 78 ;;
  esac
done
cd /app/apps/api
alembic upgrade head
exec uvicorn vigil_api.main:app --host 0.0.0.0 --port 8000
