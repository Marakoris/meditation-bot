# handlers/meditation.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime

from keyboards import get_main_keyboard, get_rating_keyboard
from states import MeditationStates

async def start_meditation(message: types.Message, db, config):
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

async def end_meditation(message: types.Message, state: FSMContext, db, config):
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

async def process_comment(message: types.Message, state: FSMContext, db):
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

async def process_rating(callback: types.CallbackQuery, state: FSMContext, db, ai, config):
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
