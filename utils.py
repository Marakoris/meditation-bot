# utils.py
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class MarathonManager:
    """Менеджер для работы с марафонами"""
    
    def __init__(self, db, ai_service, bot):
        self.db = db
        self.ai = ai_service
        self.bot = bot
    
    async def check_marathon_completions(self):
        """Проверка завершенных марафонов и отправка отчетов"""
        while True:
            try:
                # Получаем марафоны, которые завершились вчера
                yesterday = (datetime.now() - timedelta(days=1)).date()
                
                async with self.db.pool.acquire() as conn:
                    marathons = await conn.fetch('''
                        SELECT * FROM marathons
                        WHERE end_date = $1
                    ''', yesterday)
                    
                    for marathon in marathons:
                        await self._process_marathon_completion(dict(marathon))
                
            except Exception as e:
                logger.error(f"Error in marathon completion check: {e}")
            
            # Проверяем раз в день в 10:00
            await asyncio.sleep(86400)  # 24 часа
    
    async def _process_marathon_completion(self, marathon: Dict[str, Any]):
        """Обработка завершения марафона"""
        marathon_id = marathon['marathon_id']
        
        # Получаем всех участников
        async with self.db.pool.acquire() as conn:
            participants = await conn.fetch('''
                SELECT user_id FROM marathon_participants
                WHERE marathon_id = $1
            ''', marathon_id)
        
        # Отправляем каждому участнику персональный отчет
        for participant in participants:
            user_id = participant['user_id']
            
            # Получаем статистику участника
            stats = await self._get_marathon_user_stats(user_id, marathon_id)
            
            # Генерируем отчет
            report = await self._generate_personal_report(stats, marathon)
            
            # Отправляем отчет
            try:
                await self.bot.send_message(user_id, report, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to send report to user {user_id}: {e}")
        
        # Генерируем и отправляем общую статистику
        group_stats = await self._get_marathon_group_stats(marathon_id)
        await self._send_group_statistics(marathon, group_stats)
    
    async def _get_marathon_user_stats(self, user_id: int, marathon_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя в марафоне"""
        async with self.db.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as sessions_count,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(AVG(rating), 0) as avg_rating,
                    COUNT(DISTINCT DATE(start_time)) as unique_days
                FROM sessions
                WHERE user_id = $1 AND marathon_id = $2 AND end_time IS NOT NULL
            ''', user_id, marathon_id)
            
            marathon_info = await self.db.get_marathon(marathon_id)
            progress = await self.db.get_marathon_progress(user_id, marathon_id)
            
            return {
                **dict(stats),
                **progress,
                'marathon_info': marathon_info
            }
    
    async def _generate_personal_report(self, stats: Dict[str, Any], marathon: Dict[str, Any]) -> str:
        """Генерация персонального отчета"""
        # Генерируем сводку от ИИ
        ai_summary = await self.ai.generate_marathon_summary(stats, marathon)
        
        report = f"""🏆 **Марафон "{marathon['title']}" завершен!**

📊 **Ваши результаты:**
• Выполнено дней: {stats['completed_days']}/{stats['total_days']}
• Всего медитаций: {stats['sessions_count']}
• Общее время: {int(stats['total_duration'])} минут
• Средняя оценка: {stats['avg_rating']:.1f}/10

💭 **Персональная обратная связь:**
{ai_summary}

Спасибо за участие! Продолжайте практиковать 🧘"""
        
        return report
    
    async def _get_marathon_group_stats(self, marathon_id: int) -> Dict[str, Any]:
        """Получение групповой статистики марафона"""
        async with self.db.pool.acquire() as conn:
            # Общее количество участников
            total_participants = await conn.fetchval('''
                SELECT COUNT(*) FROM marathon_participants
                WHERE marathon_id = $1
            ''', marathon_id)
            
            # Участники, выполнившие хотя бы одну медитацию
            active_participants = await conn.fetchval('''
                SELECT COUNT(DISTINCT user_id) FROM sessions
                WHERE marathon_id = $1 AND end_time IS NOT NULL
            ''', marathon_id)
            
            # Участники, достигшие цели
            marathon_info = await self.db.get_marathon(marathon_id)
            goal_achievers = await conn.fetchval('''
                WITH user_days AS (
                    SELECT 
                        user_id,
                        COUNT(DISTINCT DATE(start_time)) as days_completed
                    FROM sessions
                    WHERE marathon_id = $1 AND end_time IS NOT NULL
                    GROUP BY user_id
                )
                SELECT COUNT(*) FROM user_days
                WHERE days_completed >= $2
            ''', marathon_id, 
            (marathon_info['end_date'] - marathon_info['start_date']).days * 0.8)  # 80% дней
            
            # Общая статистика
            total_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(AVG(duration), 0) as avg_duration,
                    COALESCE(AVG(rating), 0) as avg_rating
                FROM sessions
                WHERE marathon_id = $1 AND end_time IS NOT NULL
            ''', marathon_id)
            
            return {
                'total_participants': total_participants,
                'active_participants': active_participants,
                'goal_achievers': goal_achievers,
                **dict(total_stats)
            }
    
    async def _send_group_statistics(self, marathon: Dict[str, Any], stats: Dict[str, Any]):
        """Отправка групповой статистики администраторам"""
        # Здесь можно отправить статистику в специальный канал или администраторам
        completion_rate = (stats['active_participants'] / stats['total_participants'] * 100) if stats['total_participants'] > 0 else 0
        
        report = f"""📊 **Итоги марафона "{marathon['title']}"**

👥 **Участники:**
• Всего зарегистрировано: {stats['total_participants']}
• Активных участников: {stats['active_participants']} ({completion_rate:.1f}%)
• Достигли цели: {stats['goal_achievers']}

🧘 **Статистика медитаций:**
• Всего сессий: {stats['total_sessions']}
• Общее время: {int(stats['total_duration'])} минут
• Среднее время сессии: {int(stats['avg_duration'])} минут
• Средняя оценка: {stats['avg_rating']:.1f}/10

Марафон успешно завершен! 🎉"""
        
        # Отправляем администраторам
        from config import Config
        config = Config()
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(admin_id, report, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Failed to send group stats to admin {admin_id}: {e}")

def format_duration(minutes: int) -> str:
    """Форматирование продолжительности"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f"{hours} ч {mins} мин"
    else:
        return f"{mins} мин"

def get_meditation_streak(sessions: List[Dict[str, Any]]) -> int:
    """Подсчет текущей серии медитаций (дней подряд)"""
    if not sessions:
        return 0
    
    dates = sorted([s['start_time'].date() for s in sessions], reverse=True)
    streak = 1
    
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] - timedelta(days=1):
            streak += 1
        else:
            break
    
    return streak

async def send_daily_reminder(bot, db):
    """Отправка ежедневных напоминаний участникам марафонов"""
    while True:
        try:
            current_time = datetime.now()
            
            # Отправляем напоминания в 9:00
            if current_time.hour == 9 and current_time.minute == 0:
                async with db.pool.acquire() as conn:
                    # Получаем участников активных марафонов
                    participants = await conn.fetch('''
                        SELECT DISTINCT mp.user_id, m.title, m.daily_goal
                        FROM marathon_participants mp
                        JOIN marathons m ON mp.marathon_id = m.marathon_id
                        WHERE m.start_date <= CURRENT_DATE 
                        AND m.end_date >= CURRENT_DATE
                    ''')
                    
                    for participant in participants:
                        # Проверяем, сколько медитаций сделано сегодня
                        today_sessions = await conn.fetchval('''
                            SELECT COUNT(*) FROM sessions
                            WHERE user_id = $1 
                            AND DATE(start_time) = CURRENT_DATE
                            AND end_time IS NOT NULL
                        ''', participant['user_id'])
                        
                        if today_sessions < participant['daily_goal']:
                            remaining = participant['daily_goal'] - today_sessions
                            message = (
                                f"🔔 Напоминание о марафоне «{participant['title']}»\n\n"
                                f"Сегодня осталось выполнить: {remaining} медитаций\n"
                                f"Не забудьте о своей практике! 🧘"
                            )
                            
                            try:
                                await bot.send_message(
                                    participant['user_id'], 
                                    message
                                )
                            except Exception as e:
                                logger.error(f"Failed to send reminder: {e}")
            
            # Ждем минуту перед следующей проверкой
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in daily reminder: {e}")
            await asyncio.sleep(60)
