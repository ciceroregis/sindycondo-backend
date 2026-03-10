FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .
RUN pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir -r requirements.prod.txt

COPY . .

RUN chmod +x entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
