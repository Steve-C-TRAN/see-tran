#!/bin/sh
set -eu

PORT_TO_USE="${PORT:-8000}"
FLASK_ENV_TO_USE="${FLASK_ENV:-unset}"

echo "BOOT source=start_web.sh"
echo "BOOT launch_gunicorn PORT=${PORT_TO_USE} FLASK_ENV=${FLASK_ENV_TO_USE}"

exec gunicorn \
  --workers 1 \
  --bind "0.0.0.0:${PORT_TO_USE}" \
  --timeout 120 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  run:app