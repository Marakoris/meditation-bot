# config.py
from dotenv import load_dotenv
load_dotenv()

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Config:
    """Конфигурация приложения"""
    
    # Bot
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    
    # Database
    DATABASE_URL: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", 
        "postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot"
    ))
    
    # AI Service
    AI_API_KEY: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    AI_SERVICE: str = field(default_factory=lambda: os.getenv("AI_SERVICE", "openrouter"))
    AI_MODEL: str = field(default_factory=lambda: os.getenv("AI_MODEL", "anthropic/claude-3-haiku"))
    
    # Admin IDs
    ADMIN_IDS: list[int] = field(default_factory=lambda: [
        int(id.strip()) 
        for id in os.getenv("ADMIN_IDS", "").split(",") 
        if id.strip()
    ])
    
    # Optional settings
    TIMEZONE: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Moscow"))
    MAX_SESSIONS_PER_DAY: int = field(default_factory=lambda: int(os.getenv("MAX_SESSIONS_PER_DAY", "10")))
    
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
