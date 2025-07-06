# handlers/marathon.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime

from keyboards import get_main_keyboard
from states import MeditationStates

async def join_marathon(message: types.Message, db):
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

async def process_marathon_join(callback: types.CallbackQuery, db):
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

async def create_marathon(message: types.Message, state: FSMContext, config):
    """Создание марафона (для админов)"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет прав для создания марафонов.")
        return
        
    await message.answer("Введите название марафона:")
    await state.set_state(MeditationStates.waiting_for_marathon_title)

async def process_marathon_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание марафона:")
    await state.set_state(MeditationStates.waiting_for_marathon_description)

async def process_marathon_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "Введите даты начала и окончания марафона в формате:\n"
        "ДД.ММ.ГГГГ - ДД.ММ.ГГГГ"
    )
    await state.set_state(MeditationStates.waiting_for_marathon_dates)

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

async def process_marathon_goal(message: types.Message, state: FSMContext, db):
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
