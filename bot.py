# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database import Database
from keyboards import get_main_keyboard
from ai_service import AIService
from states import MeditationStates

# Импорт обработчиков
from handlers import meditation, history, marathon

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
config = Config()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database(config.DATABASE_URL)
ai = AIService(config.AI_API_KEY, config.AI_SERVICE, config.AI_MODEL)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    await db.create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    is_admin = user.id in config.ADMIN_IDS
    
    await message.answer(
        f"🧘‍♂️ Добро пожаловать в бот медитаций, {user.first_name}!\n\n"
        "Я помогу вам отслеживать ваши медитации и участвовать в марафонах.\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(is_admin=is_admin)
    )

# Обработчики медитаций
@dp.message(F.text == "🧘 Начать медитацию")
async def handle_start_meditation(message: types.Message):
    await meditation.start_meditation(message, db, config)

@dp.message(F.text == "⏹️ Завершить медитацию")
async def handle_end_meditation(message: types.Message, state: FSMContext):
    await meditation.end_meditation(message, state, db, config)

@dp.message(MeditationStates.waiting_for_comment)
async def handle_process_comment(message: types.Message, state: FSMContext):
    await meditation.process_comment(message, state, db)

@dp.callback_query(MeditationStates.waiting_for_rating, F.data.startswith("rating_"))
async def handle_process_rating(callback: types.CallbackQuery, state: FSMContext):
    await meditation.process_rating(callback, state, db, ai, config)

# Обработчики марафонов
@dp.message(F.text == "🏃 Присоединиться к марафону")
async def handle_join_marathon(message: types.Message):
    await marathon.join_marathon(message, db)

@dp.callback_query(F.data.startswith("join_marathon_"))
async def handle_process_marathon_join(callback: types.CallbackQuery):
    await marathon.process_marathon_join(callback, db)

@dp.message(F.text == "👨‍💼 Создать марафон")
async def handle_create_marathon(message: types.Message, state: FSMContext):
    await marathon.create_marathon(message, state, config)

@dp.message(MeditationStates.waiting_for_marathon_title)
async def handle_marathon_title(message: types.Message, state: FSMContext):
    await marathon.process_marathon_title(message, state)

@dp.message(MeditationStates.waiting_for_marathon_description)
async def handle_marathon_description(message: types.Message, state: FSMContext):
    await marathon.process_marathon_description(message, state)

@dp.message(MeditationStates.waiting_for_marathon_dates)
async def handle_marathon_dates(message: types.Message, state: FSMContext):
    await marathon.process_marathon_dates(message, state)

@dp.message(MeditationStates.waiting_for_marathon_goal)
async def handle_marathon_goal(message: types.Message, state: FSMContext):
    await marathon.process_marathon_goal(message, state, db)

# Обработчики истории и прогресса
@dp.message(F.text == "📊 Мой прогресс")
async def my_progress(message: types.Message):
    """Показ прогресса пользователя"""
    user_id = message.from_user.id
    
    # Общая статистика
    stats = await db.get_user_stats(user_id)
    
    text = "📊 *Ваш прогресс*\n\n"
    text += f"🧘 Всего медитаций: {stats['total_sessions']}\n"
    text += f"⏱️ Общее время: {stats['total_duration']} минут\n"
    text += f"⭐ Средняя оценка: {stats['avg_rating']:.1f}/10\n\n"
    
    # Прогресс по марафонам
    marathons = await db.get_user_marathons(user_id)
    if marathons:
        text += "*Марафоны:*\n"
        for marathon in marathons:
            progress = await db.get_marathon_progress(user_id, marathon['marathon_id'])
            text += f"\n📌 {marathon['title']}\n"
            text += f"   Выполнено: {progress['completed_days']}/{progress['total_days']} дней\n"
            text += f"   Медитаций: {progress['sessions_count']}\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📖 История медитаций")
async def handle_meditation_history(message: types.Message):
    await history.meditation_history(message, db)

# Обработчики календаря
@dp.callback_query(F.data == "show_calendar")
async def handle_show_calendar(callback: types.CallbackQuery):
    await history.show_calendar(callback, db)

@dp.callback_query(F.data.startswith("cal_day_"))
async def handle_show_day_details(callback: types.CallbackQuery):
    await history.show_day_details(callback, db)

@dp.callback_query(F.data.startswith("cal_prev_") | F.data.startswith("cal_next_"))
async def handle_navigate_calendar(callback: types.CallbackQuery):
    await history.navigate_calendar(callback, db)

@dp.callback_query(F.data == "history_week")
async def handle_show_week_history(callback: types.CallbackQuery):
    await history.show_week_history(callback, db)

@dp.callback_query(F.data == "cal_ignore")
async def handle_ignore_callback(callback: types.CallbackQuery):
    await history.ignore_callback(callback)

@dp.callback_query(F.data == "back_to_history")
async def handle_back_to_history(callback: types.CallbackQuery):
    await history.back_to_history(callback, db)

async def main():
    """Основная функция запуска бота"""
    await db.init()
    
    # Импортируем утилиты для фоновых задач
    from utils import MarathonManager, send_daily_reminder
    
    # Создаем менеджер марафонов
    marathon_manager = MarathonManager(db, ai, bot)
    
    # Запускаем фоновые задачи
    asyncio.create_task(marathon_manager.check_marathon_completions())
    asyncio.create_task(send_daily_reminder(bot, db))
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
