# bot.py
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database import Database
from keyboards import get_main_keyboard, get_rating_keyboard
from ai_service import AIService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния FSM
class MeditationStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_rating = State()
    waiting_for_marathon_title = State()
    waiting_for_marathon_description = State()
    waiting_for_marathon_dates = State()
    waiting_for_marathon_goal = State()

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

@dp.message(F.text == "🧘 Начать медитацию")
async def start_meditation(message: types.Message):
    """Начало медитации"""
    user_id = message.from_user.id
    
    # Проверяем, нет ли активной медитации
    active_session = await db.get_active_session(user_id)
    if active_session:
        await message.answer(
            "❗ У вас уже есть активная медитация.\n"
            "Завершите её перед началом новой."
        )
        return
    
    # Проверяем, в каком марафоне участвует пользователь
    user_marathons = await db.get_user_marathons(user_id)
    active_marathon_id = None
    
    for marathon in user_marathons:
        if marathon['start_date'] <= datetime.now().date() <= marathon['end_date']:
            active_marathon_id = marathon['marathon_id']
            break
    
    # Создаем новую сессию
    session_id = await db.create_session(user_id, active_marathon_id)
    
    await message.answer(
        "🧘 Медитация начата!\n\n"
        "Сосредоточьтесь на практике.\n"
        "Когда закончите, нажмите «Завершить медитацию».",
        reply_markup=get_main_keyboard(meditation_active=True, is_admin=message.from_user.id in config.ADMIN_IDS)
    )

@dp.message(F.text == "⏹️ Завершить медитацию")
async def end_meditation(message: types.Message, state: FSMContext):
    """Завершение медитации"""
    user_id = message.from_user.id
    
    # Проверяем активную сессию
    session = await db.get_active_session(user_id)
    if not session:
        await message.answer(
            "❗ У вас нет активной медитации.",
            reply_markup=get_main_keyboard(is_admin=message.from_user.id in config.ADMIN_IDS)
        )
        return
    
    # Завершаем сессию
    duration = await db.end_session(session['session_id'])
    
    # Сохраняем данные в состояние
    await state.update_data(session_id=session['session_id'], duration=duration)
    
    await message.answer(
        f"✅ Медитация завершена!\n"
        f"Продолжительность: {duration} минут\n\n"
        "Пожалуйста, поделитесь своими впечатлениями:"
    )
    await state.set_state(MeditationStates.waiting_for_comment)

@dp.message(MeditationStates.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    """Обработка комментария"""
    comment = message.text
    data = await state.get_data()
    
    # Сохраняем комментарий
    await db.update_session_comment(data['session_id'], comment)
    await state.update_data(comment=comment)
    
    await message.answer(
        "Спасибо за отзыв!\n\n"
        "Оцените вашу медитацию от 1 до 10:",
        reply_markup=get_rating_keyboard()
    )
    await state.set_state(MeditationStates.waiting_for_rating)

@dp.callback_query(MeditationStates.waiting_for_rating, F.data.startswith("rating_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    """Обработка оценки"""
    rating = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    # Сохраняем оценку
    await db.update_session_rating(data['session_id'], rating)
    
    # Генерируем отзыв от ИИ
    ai_feedback = await ai.generate_feedback(
        comment=data['comment'],
        duration=data['duration'],
        rating=rating
    )
    
    await callback.message.edit_text(
        f"🌟 Ваша оценка: {rating}/10\n\n"
        f"🤖 Персональная обратная связь:\n\n{ai_feedback}",
        reply_markup=None
    )
    
    await callback.message.answer(
        "Отлично! Ваша медитация сохранена.",
        reply_markup=get_main_keyboard(is_admin=callback.from_user.id in config.ADMIN_IDS)
    )
    
    await state.clear()
    await callback.answer()

@dp.message(F.text == "🏃 Присоединиться к марафону")
async def join_marathon(message: types.Message):
    """Присоединение к марафону"""
    user_id = message.from_user.id
    
    # Получаем активные марафоны
    marathons = await db.get_active_marathons()
    
    if not marathons:
        await message.answer(
            "🚫 Сейчас нет активных марафонов.\n"
            "Следите за обновлениями!"
        )
        return
    
    # Формируем список марафонов
    text = "🏃 Доступные марафоны:\n\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    for marathon in marathons:
        text += f"📌 *{marathon['title']}*\n"
        text += f"📅 {marathon['start_date']} - {marathon['end_date']}\n"
        text += f"🎯 Цель: {marathon['daily_goal']} медитаций в день\n"
        text += f"📝 {marathon['description']}\n\n"
        
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(
                text=f"Присоединиться к «{marathon['title']}»",
                callback_data=f"join_marathon_{marathon['marathon_id']}"
            )
        ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("join_marathon_"))
async def process_marathon_join(callback: types.CallbackQuery):
    """Обработка присоединения к марафону"""
    marathon_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Проверяем, не участвует ли уже
    is_participant = await db.is_marathon_participant(user_id, marathon_id)
    if is_participant:
        await callback.answer("Вы уже участвуете в этом марафоне!", show_alert=True)
        return
    
    # Добавляем участника
    await db.add_marathon_participant(user_id, marathon_id)
    marathon = await db.get_marathon(marathon_id)
    
    await callback.message.edit_text(
        f"✅ Вы присоединились к марафону «{marathon['title']}»!\n\n"
        f"🎯 Ваша цель: {marathon['daily_goal']} медитаций в день\n"
        f"📅 До конца марафона: {(marathon['end_date'] - datetime.now().date()).days} дней\n\n"
        "Удачи в практике! 🧘"
    )
    await callback.answer()

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
async def meditation_history(message: types.Message):
    """История медитаций"""
    user_id = message.from_user.id
    sessions = await db.get_user_sessions(user_id, limit=15)
    
    if not sessions:
        await message.answer("У вас пока нет завершенных медитаций.")
        return
    
    # Получаем общую статистику
    stats = await db.get_user_stats(user_id)
    total_sessions = stats['total_sessions']
    
    # Получаем статистику за последние 30 дней
    monthly_stats = await db.get_monthly_stats(user_id)
    
    text = "📖 *История медитаций*\n\n"
    text += f"📊 *Общая статистика:*\n"
    text += f"• Всего медитаций: {total_sessions}\n"
    text += f"• За последние 30 дней: {monthly_stats['sessions_count']}\n"
    text += f"• Средняя оценка за месяц: {monthly_stats['avg_rating']:.1f}/10\n"
    text += f"• Всего времени: {stats['total_duration']} мин\n\n"
    
    text += f"*Последние 15 медитаций:*\n\n"
    
    for session in sessions:
        date = session['start_time'].strftime("%d.%m.%Y %H:%M")
        text += f"🧘 {date}\n"
        text += f"   ⏱️ {session['duration']} мин | ⭐ {session['rating']}/10\n"
        if session['comment']:
            # Умная обрезка комментария
            comment = session['comment']
            if len(comment) > 100:
                # Обрезаем до последнего пробела перед 100 символом
                cut_pos = comment[:100].rfind(' ')
                if cut_pos > 80:  # Если пробел найден после 80 символа
                    comment = comment[:cut_pos] + "..."
                else:
                    comment = comment[:100] + "..."
            text += f"   💭 {comment}\n"
        text += "\n"
    
    # Добавляем кнопки для дополнительных действий
    keyboard = get_history_keyboard()
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message(F.text == "👨‍💼 Создать марафон")
async def create_marathon(message: types.Message, state: FSMContext):
    """Создание марафона (для админов)"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет прав для создания марафонов.")
        return
        
    await message.answer("Введите название марафона:")
    await state.set_state(MeditationStates.waiting_for_marathon_title)

# Обработчики для создания марафона
@dp.message(MeditationStates.waiting_for_marathon_title)
async def process_marathon_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание марафона:")
    await state.set_state(MeditationStates.waiting_for_marathon_description)

@dp.message(MeditationStates.waiting_for_marathon_description)
async def process_marathon_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "Введите даты начала и окончания марафона в формате:\n"
        "ДД.ММ.ГГГГ - ДД.ММ.ГГГГ"
    )
    await state.set_state(MeditationStates.waiting_for_marathon_dates)

@dp.message(MeditationStates.waiting_for_marathon_dates)
async def process_marathon_dates(message: types.Message, state: FSMContext):
    try:
        dates = message.text.split(" - ")
        start_date = datetime.strptime(dates[0], "%d.%m.%Y").date()
        end_date = datetime.strptime(dates[1], "%d.%m.%Y").date()
        
        await state.update_data(start_date=start_date, end_date=end_date)
        await message.answer("Введите цель по количеству медитаций в день:")
        await state.set_state(MeditationStates.waiting_for_marathon_goal)
    except:
        await message.answer("Неверный формат дат. Попробуйте еще раз:")

@dp.message(MeditationStates.waiting_for_marathon_goal)
async def process_marathon_goal(message: types.Message, state: FSMContext):
    try:
        daily_goal = int(message.text)
        data = await state.get_data()
        
        marathon_id = await db.create_marathon(
            title=data['title'],
            description=data['description'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            daily_goal=daily_goal
        )
        
        await message.answer(
            f"✅ Марафон «{data['title']}» создан!\n\n"
            f"ID: {marathon_id}\n"
            f"Даты: {data['start_date']} - {data['end_date']}\n"
            f"Цель: {daily_goal} медитаций в день",
            reply_markup=get_main_keyboard(is_admin=True)
        )
        await state.clear()
    except ValueError:
        await message.answer("Введите число:")

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
