#!/bin/sh
set -e

echo "==> Aplicando migrations..."
python manage.py migrate --noinput

echo "==> Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "==> Iniciando servidor ASGI..."
exec gunicorn sindycondo.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --worker-connections 1000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
