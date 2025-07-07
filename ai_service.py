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

class OpenRouterProvider(AIProvider):
    """Провайдер для OpenRouter API"""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3-haiku"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def generate_feedback(self, comment: str, duration: int, rating: int) -> str:
        prompt = f"""Ты - опытный инструктор медитации. Пользователь завершил медитацию:
- Продолжительность: {duration} минут
- Оценка: {rating}/10
- Комментарий: {comment}

Дай персональную, поддерживающую обратную связь (3-4 предложения).
Учти оценку и комментарий. Будь конкретным и практичным."""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/Marakoris/meditation-bot",
            "X-Title": "Meditation Bot"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты опытный и заботливый инструктор медитации. Давай краткую, но полезную обратную связь."
                },
                {
                    "role": "user",
                    "content": prompt
                }
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
                        error_data = await response.text()
                        logger.error(f"OpenRouter API error: {response.status} - {error_data}")
                        return self._get_fallback_feedback(rating)
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return self._get_fallback_feedback(rating)
    
    def _get_fallback_feedback(self, rating: int) -> str:
        if rating >= 8:
            return "Отличная практика! Продолжайте в том же духе и наблюдайте за положительными изменениями."
        elif rating >= 5:
            return "Хорошая медитация! Регулярная практика поможет углубить ваш опыт."
        else:
            return "Каждая медитация - это шаг вперед. Продолжайте практиковать, и результаты придут."

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
    
    def __init__(self, api_key: str, provider: str = "openrouter", model: str = None):
        self.provider = self._get_provider(api_key, provider, model)
    
    def _get_provider(self, api_key: str, provider: str, model: str = None) -> AIProvider:
        if provider.lower() == "openrouter":
            # Рекомендуемые модели для OpenRouter:
            # - anthropic/claude-3-haiku (быстрый и дешевый)
            # - anthropic/claude-3-sonnet (баланс)
            # - openai/gpt-3.5-turbo (дешевый)
            # - openai/gpt-4-turbo (мощный)
            # - google/gemini-pro (бесплатный лимит)
            # - meta-llama/llama-3-8b-instruct (дешевый)
            default_model = model or "anthropic/claude-3-haiku"
            return OpenRouterProvider(api_key, default_model)
        elif provider.lower() == "claude":
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
        prompt = f"""Создай мотивирующий итоговый отчет по марафону медитаций:
- Название марафона: {marathon_info['title']}
- Продолжительность: {marathon_info['total_days']} дней
- Цель: {marathon_info['daily_goal']} медитаций в день
- Выполнено дней: {user_stats['completed_days']}
- Всего медитаций: {user_stats['sessions_count']}
- Общее время: {user_stats['total_duration']} минут
- Средняя оценка: {user_stats['avg_rating']}/10

Отчет должен быть позитивным, отмечать достижения и мотивировать на дальнейшую практику."""
        
        # Используем generate_feedback с модифицированным промптом
        return await self.provider.generate_feedback(prompt, 0, 10)
    
    async def generate_dialogue_response(self, message: str, history: str, 
                                       system_prompt: str, dialogue_prompt: str) -> str:
        """Генерация ответа в диалоге с учетом истории"""
        if isinstance(self.provider, OpenRouterProvider):
            formatted_prompt = dialogue_prompt.format(
                history=history,
                message=message
            )
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.provider.api_key}",
                "HTTP-Referer": "https://github.com/Marakoris/meditation-bot",
                "X-Title": "Meditation Bot"
            }
            
            payload = {
                "model": self.provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.8
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.provider.base_url,
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data['choices'][0]['message']['content']
                        else:
                            return "Извините, не могу ответить сейчас. Попробуйте позже."
            except Exception as e:
                logger.error(f"Error in dialogue: {e}")
                return "Произошла ошибка. Попробуйте позже."
        else:
            # Для других провайдеров используем базовый метод
            return await self.provider.generate_feedback(message, 0, 8)
    
    async def parse_meditation_entry(self, message: str) -> str:
        """Парсинг свободной формы записи медитации"""
        from prompts import PARSE_MEDITATION_PROMPT
        
        prompt = PARSE_MEDITATION_PROMPT.format(message=message)
        
        if isinstance(self.provider, OpenRouterProvider):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.provider.api_key}",
                "HTTP-Referer": "https://github.com/Marakoris/meditation-bot",
                "X-Title": "Meditation Bot"
            }
            
            payload = {
                "model": self.provider.model,
                "messages": [
                    {"role": "system", "content": "Ты - помощник для парсинга текста. Всегда отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.3
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.provider.base_url,
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data['choices'][0]['message']['content']
                        else:
                            return '{"confidence": false, "clarification_needed": "информацию о медитации"}'
            except Exception as e:
                logger.error(f"Error parsing meditation: {e}")
                return '{"confidence": false, "clarification_needed": "информацию о медитации"}'
        else:
            return '{"confidence": false, "clarification_needed": "информацию о медитации"}'

    async def get_progress_analysis(self, data: dict) -> str:
        """Генерирует текстовый анализ прогресса пользователя."""
        from prompts import PROGRESS_ANALYSIS_PROMPT

        # Тренд вычисляем по средним оценкам первой и второй половины
        ratings = [s.get("rating") for s in data.get("recent_sessions", []) if s.get("rating") is not None]
        trend = "недостаточно данных"
        if len(ratings) >= 2:
            half = len(ratings) // 2
            first_avg = sum(ratings[:half]) / half
            last_avg = sum(ratings[half:]) / len(ratings[half:])
            delta = last_avg - first_avg
            if delta > 0.5:
                trend = "растущий"
            elif delta < -0.5:
                trend = "падающий"
            else:
                trend = "стабильный"

        prompt = PROGRESS_ANALYSIS_PROMPT.format(
            total_sessions=data.get('total_sessions', 0),
            total_duration=data.get('total_duration', 0),
            avg_rating=data.get('avg_rating', 0),
            month_sessions=data.get('monthly_sessions', 0),
            rating_trend=trend
        )

        # Используем провайдера, как и в генерации отчетов
        return await self.provider.generate_feedback(prompt, 0, 10)
