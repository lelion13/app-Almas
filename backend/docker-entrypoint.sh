#!/bin/sh
set -e

if [ "${SKIP_DB_MIGRATE:-0}" != "1" ]; then
  echo "Running alembic upgrade head..."
  alembic upgrade head
fi

exec "$@"
