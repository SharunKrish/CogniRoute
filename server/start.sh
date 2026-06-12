#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "==> Running Django Migrations..."
python manage.py migrate --noinput

echo "==> Seeding Database..."
python seed_db.py

echo "==> Collecting Static Files..."
python manage.py collectstatic --noinput

echo "==> Starting Celery Worker in background..."
celery -A cogniroute worker --loglevel=info -P solo &

echo "==> Starting Daphne ASGI Server..."
# Daphne will bind to $PORT or default 8000
PORT_NUM=${PORT:-8000}
daphne -b 0.0.0.0 -p $PORT_NUM cogniroute.asgi:application
