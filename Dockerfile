FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Установка зависимостей системы только если нужно
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     some-package \
#     && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY WikipediaBot.py .
COPY .env.example .

# Создаем непривилегированного пользователя (для безопасности)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Запускаем бота
CMD ["python", "WikipediaBot.py"]