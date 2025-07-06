# ai_service.py
import aiohttp
import json
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Абстрактный класс для провайдеров ИИ"""
    
    @abstractmethod
    async def generate_feedback(self, comment: str, duration: int, rating: int) -> str:
        pass

class ClaudeProvider(AIProvider):
    """Провайдер для Claude API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    async def generate_feedback(self, comment: str, duration: int, rating: int) -> str:
        prompt = f"""Ты - опытный инструктор медитации. Пользователь завершил медитацию:
- Продолжительность: {duration} минут
- Оценка: {rating}/10
- Комментарий: {comment}

Дай персональную, поддерживающую обратную связь (3-4 предложения).
Учти оценку и комментарий. Будь конкретным и практичным."""

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['content'][0]['text']
                    else:
                        logger.error(f"Claude API error: {response.status}")
                        return self._get_fallback_feedback(rating)
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return self._get_fallback_feedback(rating)
    
    def _get_fallback_feedback(self, rating: int) -> str:
        if rating >= 8:
            return "Отличная практика! Продолжайте в том же духе и наблюдайте за положительными изменениями."
        elif rating >= 5:
            return "Хорошая медитация! Регулярная практика поможет углубить ваш опыт."
        else:
            return "Каждая медитация - это шаг вперед. Продолжайте практиковать, и результаты придут."

class OpenAIProvider(AIProvider):
    """Провайдер для OpenAI API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def generate_feedback(self, comment: str, duration: int, rating: int) -> str:
        prompt = f"""Ты - опытный инструктор медитации. Пользователь завершил медитацию:
- Продолжительность: {duration} минут
- Оценка: {rating}/10
- Комментарий: {comment}

Дай персональную, поддерживающую обратную связь (3-4 предложения).
Учти оценку и комментарий. Будь конкретным и практичным."""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Ты опытный и заботливый инструктор медитации."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return self._get_fallback_feedback(rating)
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return self._get_fallback_feedback(rating)
    
    def _get_fallback_feedback(self, rating: int) -> str:
        if rating >= 8:
            return "Отличная практика! Продолжайте в том же духе и наблюдайте за положительными изменениями."
        elif rating >= 5:
            return "Хорошая медитация! Регулярная практика поможет углубить ваш опыт."
        else:
            return "Каждая медитация - это шаг вперед. Продолжайте практиковать, и результаты придут."

class AIService:
    """Сервис для работы с ИИ"""
    
    def __init__(self, api_key: str, provider: str = "claude"):
        self.provider = self._get_provider(api_key, provider)
    
    def _get_provider(self, api_key: str, provider: str) -> AIProvider:
        if provider.lower() == "claude":
            return ClaudeProvider(api_key)
        elif provider.lower() == "openai":
            return OpenAIProvider(api_key)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    async def generate_feedback(self, comment: str, duration: int, rating: int) -> str:
        """Генерация персональной обратной связи"""
        return await self.provider.generate_feedback(comment, duration, rating)
    
    async def generate_marathon_summary(self, user_stats: dict, marathon_info: dict) -> str:
        """Генерация итогового отчета по марафону"""
        if isinstance(self.provider, ClaudeProvider):
            prompt = f"""Создай мотивирующий итоговый отчет по марафону медитаций:
- Название марафона: {marathon_info['title']}
- Продолжительность: {marathon_info['total_days']} дней
- Цель: {marathon_info['daily_goal']} медитаций в день
- Выполнено дней: {user_stats['completed_days']}
- Всего медитаций: {user_stats['sessions_count']}
- Общее время: {user_stats['total_duration']} минут
- Средняя оценка: {user_stats['avg_rating']}/10

Отчет должен быть позитивным, отмечать достижения и мотивировать на дальнейшую практику."""
            
            return await self.provider.generate_feedback(prompt, 0, 10)
        else:
            # Для OpenAI используем тот же подход
            return await self.provider.generate_feedback(
                f"Марафон '{marathon_info['title']}' завершен. "
                f"Выполнено {user_stats['completed_days']} дней из {marathon_info['total_days']}.",
                user_stats['total_duration'],
                int(user_stats['avg_rating'])
            )
