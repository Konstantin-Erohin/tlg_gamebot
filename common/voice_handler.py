import whisper
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Глобальная переменная для модели (загружается один раз)
_whisper_model = None

def get_whisper_model():
    """
    Ленивая загрузка модели whisper.
    Загружается один раз при первом вызове.
    """
    global _whisper_model
    
    if _whisper_model is None:
        logger.info("Загрузка модели Whisper (base)...")
        # В Docker можно указать модель через переменную окружения
        model_name = os.getenv('WHISPER_MODEL', 'base')
        try:
            _whisper_model = whisper.load_model(model_name)
            logger.info(f"Модель Whisper ({model_name}) загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели Whisper: {e}")
            raise
    
    return _whisper_model

async def transcribe_voice_message(bot, file_id: str) -> str:
    """
    Скачивает голосовое сообщение из Telegram и расшифровывает его.
    
    Args:
        bot: Экземпляр бота Telegram
        file_id: ID файла в Telegram
    
    Returns:
        str: Расшифрованный текст
    """
    temp_path = None
    try:
        # Получаем информацию о файле
        file_info = await bot.get_file(file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.oga', delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        # Скачиваем файл
        await bot.download_file(file_info.file_path, temp_path)
        
        # Получаем модель
        model = get_whisper_model()
        
        # Расшифровка
        result = model.transcribe(temp_path, fp16=False)
        text = result["text"].strip()
        
        return text if text else "Не удалось распознать речь"
        
    except Exception as e:
        logger.error(f"Ошибка расшифровки аудио: {e}")
        raise
    finally:
        # Удаляем временный файл в любом случае
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_path}: {e}")