#!/usr/bin/env bash
set -e
echo "=== PeerLearn Starting ==="
echo "Python: $(python3 --version)"
echo "PORT: ${PORT:-8000}"
exec gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
