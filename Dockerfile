# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Создаём рабочую директорию
WORKDIR /app

# Копируем только файлы с зависимостями для кеширования слоя
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости через uv sync (без dev-зависимостей)
RUN uv sync --frozen --no-dev

# Копируем исходный код (исключая то, что в .dockerignore)
COPY . .

# Создаём volume для логов и базы данных (монтируются как отдельные файлы)
VOLUME ["/app/logs.txt", "/app/database.db"]

# Переменная окружения для корректного вывода логов
ENV PYTHONUNBUFFERED=1

# Запускаем бота через uv run, чтобы подхватить виртуальное окружение
CMD ["uv", "run", "python3", "app.py"]