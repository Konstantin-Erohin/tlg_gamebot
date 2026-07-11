# Используем Python 3.10+ для лучшей совместимости с whisper
FROM python:3.10-slim

# Устанавливаем системные зависимости для whisper
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Создаём рабочую директорию
WORKDIR /app

# Копируем только файлы с зависимостями для кеширования слоя
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости через uv sync (без dev-зависимостей)
RUN uv sync --frozen --no-dev

# Предзагружаем модель whisper (опционально, ускоряет первый запуск)
#RUN mkdir -p /root/.cache/whisper && \
#    python3 -c "import whisper; whisper.load_model('base')" && \
#    echo "Модель Whisper загружена"

# Копируем исходный код (исключая то, что в .dockerignore)
COPY . .

# Создаём volume для логов и базы данных (монтируются как отдельные файлы)
VOLUME ["/app/logs.txt", "/app/database.db", "/root/.cache/whisper"]

# Переменная окружения для корректного вывода логов
ENV PYTHONUNBUFFERED=1
# Модель whisper по умолчанию
ENV WHISPER_MODEL=base

# Запускаем бота через uv run, чтобы подхватить виртуальное окружение
CMD ["uv", "run", "python3", "app.py"]