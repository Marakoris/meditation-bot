# database.py
import asyncpg
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init(self):
        """Инициализация пула соединений и создание таблиц"""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self.create_tables()
    
    async def create_tables(self):
        """Создание необходимых таблиц"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    duration INTEGER,
                    comment TEXT,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 10),
                    marathon_id INTEGER
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS marathons (
                    marathon_id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    daily_goal INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS marathon_participants (
                    user_id BIGINT REFERENCES users(user_id),
                    marathon_id INTEGER REFERENCES marathons(marathon_id),
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, marathon_id)
                )
            ''')
            
            # Создаем индексы для оптимизации
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON sessions(user_id)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_marathon_id 
                ON sessions(marathon_id)
            ''')
    
    # Методы для работы с пользователями
    async def create_user(self, user_id: int, username: Optional[str],
                         first_name: Optional[str], last_name: Optional[str]):
        """Создание или обновление пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
            ''', user_id, username, first_name, last_name)
    
    # Методы для работы с сессиями
    async def create_session(self, user_id: int, marathon_id: Optional[int] = None) -> int:
        """Создание новой сессии медитации"""
        async with self.pool.acquire() as conn:
            session_id = await conn.fetchval('''
                INSERT INTO sessions (user_id, marathon_id)
                VALUES ($1, $2)
                RETURNING session_id
            ''', user_id, marathon_id)
            return session_id
    
    async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение активной сессии пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM sessions
                WHERE user_id = $1 AND end_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            ''', user_id)
            return dict(row) if row else None
    
    async def end_session(self, session_id: int) -> int:
        """Завершение сессии и расчет продолжительности"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''
                UPDATE sessions
                SET end_time = CURRENT_TIMESTAMP,
                    duration = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time)) / 60
                WHERE session_id = $1
                RETURNING duration
            ''', session_id)
            return int(result['duration'])
    
    async def update_session_comment(self, session_id: int, comment: str):
        """Обновление комментария сессии"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE sessions
                SET comment = $2
                WHERE session_id = $1
            ''', session_id, comment)
    
    async def update_session_rating(self, session_id: int, rating: int):
        """Обновление оценки сессии"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE sessions
                SET rating = $2
                WHERE session_id = $1
            ''', session_id, rating)
    
    async def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории сессий пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM sessions
                WHERE user_id = $1 AND end_time IS NOT NULL
                ORDER BY start_time DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(AVG(rating), 0) as avg_rating
                FROM sessions
                WHERE user_id = $1 AND end_time IS NOT NULL
            ''', user_id)
            return dict(stats)
    
    # Методы для работы с марафонами
    async def create_marathon(self, title: str, description: str,
                            start_date: date, end_date: date, daily_goal: int) -> int:
        """Создание нового марафона"""
        async with self.pool.acquire() as conn:
            marathon_id = await conn.fetchval('''
                INSERT INTO marathons (title, description, start_date, end_date, daily_goal)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING marathon_id
            ''', title, description, start_date, end_date, daily_goal)
            return marathon_id
    
    async def get_active_marathons(self) -> List[Dict[str, Any]]:
        """Получение активных марафонов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM marathons
                WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE
                ORDER BY start_date
            ''')
            return [dict(row) for row in rows]
    
    async def get_marathon(self, marathon_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о марафоне"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM marathons
                WHERE marathon_id = $1
            ''', marathon_id)
            return dict(row) if row else None
    
    async def add_marathon_participant(self, user_id: int, marathon_id: int):
        """Добавление участника в марафон"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO marathon_participants (user_id, marathon_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            ''', user_id, marathon_id)
    
    async def is_marathon_participant(self, user_id: int, marathon_id: int) -> bool:
        """Проверка участия в марафоне"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval('''
                SELECT EXISTS(
                    SELECT 1 FROM marathon_participants
                    WHERE user_id = $1 AND marathon_id = $2
                )
            ''', user_id, marathon_id)
            return result
    
    async def get_user_marathons(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение марафонов пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT m.* FROM marathons m
                JOIN marathon_participants mp ON m.marathon_id = mp.marathon_id
                WHERE mp.user_id = $1
                ORDER BY m.start_date DESC
            ''', user_id)
            return [dict(row) for row in rows]
    
    async def get_marathon_progress(self, user_id: int, marathon_id: int) -> Dict[str, Any]:
        """Получение прогресса пользователя в марафоне"""
        async with self.pool.acquire() as conn:
            marathon = await self.get_marathon(marathon_id)
            
            # Считаем количество дней и выполненных дней
            total_days = (marathon['end_date'] - marathon['start_date']).days + 1
            
            # Получаем количество сессий в рамках марафона
            sessions_count = await conn.fetchval('''
                SELECT COUNT(*) FROM sessions
                WHERE user_id = $1 AND marathon_id = $2 AND end_time IS NOT NULL
            ''', user_id, marathon_id)
            
            # Считаем количество дней с выполненной целью
            completed_days = await conn.fetchval('''
                SELECT COUNT(DISTINCT DATE(start_time)) FROM sessions
                WHERE user_id = $1 AND marathon_id = $2 AND end_time IS NOT NULL
                GROUP BY DATE(start_time)
                HAVING COUNT(*) >= $3
            ''', user_id, marathon_id, marathon['daily_goal'])
            
            return {
                'total_days': total_days,
                'completed_days': completed_days or 0,
                'sessions_count': sessions_count,
                'daily_goal': marathon['daily_goal']
            }
    
    async def get_monthly_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики за последние 30 дней"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as sessions_count,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(AVG(rating), 0) as avg_rating,
                    COUNT(DISTINCT DATE(start_time)) as active_days
                FROM sessions
                WHERE user_id = $1 
                    AND end_time IS NOT NULL
                    AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            ''', user_id)
            return dict(stats)
    
    async def get_sessions_by_month(self, user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
        """Получение всех сессий за конкретный месяц"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM sessions
                WHERE user_id = $1 
                    AND end_time IS NOT NULL
                    AND EXTRACT(YEAR FROM start_time) = $2
                    AND EXTRACT(MONTH FROM start_time) = $3
                ORDER BY start_time
            ''', user_id, year, month)
            return [dict(row) for row in rows]
    
    async def get_daily_stats(self, user_id: int, date: date) -> Dict[str, Any]:
        """Получение статистики за конкретный день"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as sessions_count,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(AVG(rating), 0) as avg_rating,
                    COALESCE(MAX(rating), 0) as max_rating
                FROM sessions
                WHERE user_id = $1 
                    AND DATE(start_time) = $2
                    AND end_time IS NOT NULL
            ''', user_id, date)
            
            sessions = await conn.fetch('''
                SELECT * FROM sessions
                WHERE user_id = $1 
                    AND DATE(start_time) = $2
                    AND end_time IS NOT NULL
                ORDER BY start_time
            ''', user_id, date)
            
    async def close(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
