# Базовый образ
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Установим пакеты, нужные для установки некоторых зависимостей (минимально)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*

# Копируем только requirements и установим зависимости (кэширование слоёв)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Точка входа: запускаем бота
CMD ["python", "WikipediaBot.py"]
