# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import logging

class Settings(BaseSettings):
    # API
    API_V1_STR: str
    PROJECT_NAME: str
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Supabase
    SUPABASE_URL: str = "https://ujtenbbwwdxclabytfws.supabase.co"
    SUPABASE_KEY: str
    
    # Telegram
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_STRING: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_TO_FILE: bool = False
    LOG_FILE_PATH: str = "logs/clienthunter.log"
    
    # Performance settings
    ENABLE_DEBUG_LOGGING: bool = False  # Детальное логирование для разработки
    LOG_MESSAGE_CONTENT: bool = False   # Логировать содержимое сообщений (только для DEBUG)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def setup_logging(self):
        """Настройка системы логирования"""
        # Преобразуем строку в уровень
        level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        
        # Создаем formatter
        formatter = logging.Formatter(self.LOG_FORMAT)
        
        # Настраиваем root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Очищаем существующие handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (опционально)
        if self.LOG_TO_FILE:
            import os
            os.makedirs(os.path.dirname(self.LOG_FILE_PATH), exist_ok=True)
            file_handler = logging.FileHandler(self.LOG_FILE_PATH)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Настраиваем уровни для внешних библиотек
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('telethon').setLevel(logging.WARNING)

settings = Settings()