# config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Конфигурация приложения"""
    
    # Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/meditation_bot"
    )
    
    # AI Service (Claude API или OpenAI)
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_SERVICE: str = os.getenv("AI_SERVICE", "claude")  # claude или openai
    
    # Admin IDs
    ADMIN_IDS: list[int] = [
        int(id.strip()) 
        for id in os.getenv("ADMIN_IDS", "").split(",") 
        if id.strip()
    ]
    
    # Optional settings
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    MAX_SESSIONS_PER_DAY: int = int(os.getenv("MAX_SESSIONS_PER_DAY", "10"))
    
    def __post_init__(self):
        """Валидация конфигурации"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not self.AI_API_KEY:
            raise ValueError("AI_API_KEY is required")
        
        # Преобразуем DATABASE_URL для asyncpg если нужно
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql://", 1
            )
