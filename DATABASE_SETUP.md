# Настройка базы данных для WikiBot

Перед запуском бота необходимо создать базу данных PostgreSQL и таблицу для хранения данных.

## 1. Создание базы данных

Подключитесь к вашему серверу PostgreSQL и выполните:

```sql
CREATE DATABASE wikibot_db;
CREATE USER wikibot WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE wikibot_db TO wikibot;
```

## 2. Создание таблицы

Выполните следующий SQL-запрос в созданной базе данных:

```sql
CREATE TABLE user_interactions (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  username TEXT,
  query_text TEXT,
  response_text TEXT,
  language VARCHAR(10),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## 3. Настройка переменных окружения

Обновите файл .env с правильными параметрами подключения к вашей базе данных:

DB_HOST=your_postgres_host
DB_PORT=5432
DB_NAME=wikibot_db
DB_USER=wikibot
DB_PASSWORD=your_password

## 4. Запуск бота

После настройки базы данных запустите бота:

```bash
docker-compose up -d
```

## 5. Запуск бота

Теперь вы можете запустить бота, предварительно настроив подключение к внешней PostgreSQL в файле `.env`:

```bash
sudo docker-compose up
```

