#!/bin/sh
set -eu
cd /app/apps/api
alembic upgrade head
exec uvicorn vigil_api.main:app --host 0.0.0.0 --port 8000
