# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей для PostgreSQL и Redis
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
