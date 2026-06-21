#!/usr/bin/env bash
set -e
echo "Python version: $(python3 --version)"
echo "Starting PeerLearn with gunicorn..."
exec gunicorn wsgi:app --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120 --log-level info
