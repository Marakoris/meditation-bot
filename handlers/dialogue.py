# handlers/dialogue.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import json
import re

from keyboards import get_main_keyboard, get_confirmation_keyboard
from states import DialogueStates
from prompts import SYSTEM_PROMPT, DIALOGUE_PROMPT, PARSE_MEDITATION_PROMPT

async def start_dialogue(message: types.Message, db, ai):
    """Начать диалог с AI"""
    user_id = message.from_user.id
    
    # Получаем историю диалогов
    history = await db.get_dialogue_history(user_id, limit=10)
    
    # Формируем контекст
    context = ""
    for msg in history:
        role = "Пользователь" if msg['is_user'] else "Ассистент"
        context += f"{role}: {msg['content']}\n"
    
    # Генерируем ответ
    response = await ai.generate_dialogue_response(
        message.text,
        context,
        SYSTEM_PROMPT,
        DIALOGUE_PROMPT
    )
    
    # Сохраняем в историю
    await db.save_dialogue_message(user_id, message.text, True)
    await db.save_dialogue_message(user_id, response, False)
    
    await message.answer(response)

async def manual_meditation_entry(message: types.Message, state: FSMContext):
    """Начать ручную запись медитации"""
    await message.answer(
        "📝 *Запись медитации*\n\n"
        "Опишите вашу медитацию в свободной форме. Например:\n"
        "_'Медитировал сегодня утром 20 минут, было спокойно, оценка 8'_\n"
        "_'Вчера вечером в 22:00 практиковал 30 минут'_\n\n"
        "Я пойму ваше сообщение и создам запись.",
        parse_mode="Markdown"
    )
    await state.set_state(DialogueStates.waiting_for_manual_entry)

async def process_manual_entry(message: types.Message, state: FSMContext, db, ai):
    """Обработать ручной ввод медитации"""
    user_id = message.from_user.id
    
    # Парсим сообщение через AI
    parsed = await ai.parse_meditation_entry(message.text)
    
    try:
        data = json.loads(parsed)
    except:
        await message.answer(
            "🤔 Не смог понять ваше сообщение. "
            "Попробуйте указать время и продолжительность более явно."
        )
        return
    
    if not data.get('confidence'):
        # Нужно уточнение
        clarification = data.get('clarification_needed', 'информацию о медитации')
        await message.answer(f"🤔 Пожалуйста, уточните {clarification}")
        return
    
    # Сохраняем данные для подтверждения
    await state.update_data(
        parsed_data=data,
        original_message=message.text
    )
    
    # Формируем подтверждение
    confirmation_text = "✅ *Проверьте данные:*\n\n"
    
    # Обрабатываем дату и время
    if data['date'] == datetime.now().strftime('%Y-%m-%d'):
        confirmation_text += f"📅 Дата: Сегодня\n"
    else:
        confirmation_text += f"📅 Дата: {data['date']}\n"
    
    confirmation_text += f"🕐 Время: {data['time']}\n"
    confirmation_text += f"⏱️ Продолжительность: {data['duration']} мин\n"
    
    if data.get('rating'):
        confirmation_text += f"⭐ Оценка: {data['rating']}/10\n"
    
    if data.get('comment'):
        confirmation_text += f"💭 Комментарий: {data['comment']}\n"
    
    confirmation_text += "\nВсё верно?"
    
    await message.answer(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(DialogueStates.confirming_manual_entry)

async def confirm_manual_entry(callback: types.CallbackQuery, state: FSMContext, db):
    """Подтвердить и сохранить ручную запись"""
    if callback.data == "confirm_yes":
        data = await state.get_data()
        parsed = data['parsed_data']
        
        # Преобразуем дату и время
        date_str = parsed['date']
        time_str = parsed['time']
        datetime_str = f"{date_str} {time_str}"
        
        try:
            meditation_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except:
            meditation_time = datetime.now()
        
        # Создаем запись в БД
        session_id = await db.create_manual_session(
            user_id=callback.from_user.id,
            start_time=meditation_time,
            duration=parsed['duration'],
            rating=parsed.get('rating'),
            comment=parsed.get('comment')
        )
        
        await callback.message.edit_text(
            "✅ Медитация записана!\n\n"
            f"📅 {meditation_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏱️ {parsed['duration']} минут\n" +
            (f"⭐ Оценка: {parsed['rating']}/10\n" if parsed.get('rating') else "") +
            (f"💭 {parsed['comment']}" if parsed.get('comment') else "")
        )
        
        await state.clear()
    else:
        await callback.message.edit_text(
            "❌ Запись отменена.\n\n"
            "Попробуйте описать медитацию еще раз или используйте обычный таймер."
        )
        await state.clear()
    
    await callback.answer()

async def delete_meditation(message: types.Message, db):
    """Показать список медитаций для удаления"""
    user_id = message.from_user.id
    sessions = await db.get_user_sessions(user_id, limit=10)
    
    if not sessions:
        await message.answer("У вас нет записанных медитаций.")
        return
    
    text = "🗑️ *Выберите медитацию для удаления:*\n\n"
    keyboard = InlineKeyboardBuilder()
    
    for i, session in enumerate(sessions, 1):
        date = session['start_time'].strftime("%d.%m.%Y %H:%M")
        button_text = f"{i}. {date} ({session['duration']} мин)"
        
        text += f"{i}. {date}\n"
        text += f"   ⏱️ {session['duration']} мин | ⭐ {session['rating']}/10\n\n"
        
        keyboard.button(
            text=button_text,
            callback_data=f"delete_session_{session['session_id']}"
        )
    
    keyboard.adjust(1)
    keyboard.button(text="❌ Отмена", callback_data="cancel_delete")
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard.as_markup())

async def confirm_delete_session(callback: types.CallbackQuery, db):
    """Подтвердить удаление сессии"""
    if callback.data == "cancel_delete":
        await callback.message.edit_text("❌ Удаление отменено")
        await callback.answer()
        return
    
    session_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о сессии
    session = await db.get_session_by_id(session_id)
    
    if not session:
        await callback.answer("Сессия не найдена", show_alert=True)
        return
    
    text = (
        "⚠️ *Подтвердите удаление:*\n\n"
        f"📅 {session['start_time'].strftime('%d.%m.%Y %H:%M')}\n"
        f"⏱️ {session['duration']} минут\n"
        f"⭐ Оценка: {session['rating']}/10\n"
    )
    
    if session['comment']:
        text += f"💭 {session['comment'][:50]}...\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🗑️ Удалить", callback_data=f"confirm_delete_{session_id}")
    keyboard.button(text="❌ Отмена", callback_data="cancel_delete")
    keyboard.adjust(2)
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

async def process_delete_session(callback: types.CallbackQuery, db):
    """Удалить сессию"""
    session_id = int(callback.data.split("_")[2])
    
    # Удаляем сессию
    success = await db.delete_session(session_id, callback.from_user.id)
    
    if success:
        await callback.message.edit_text("✅ Медитация удалена")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении")
    
    await callback.answer()
