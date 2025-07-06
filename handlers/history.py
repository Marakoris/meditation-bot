# handlers/history.py
from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta, date

from keyboards import get_history_keyboard, get_calendar_keyboard

async def meditation_history(message: types.Message, db):
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

async def show_calendar(callback: types.CallbackQuery, db):
    """Показать календарь текущего месяца"""
    now = datetime.now()
    
    # Получаем данные о медитациях за месяц
    sessions = await db.get_sessions_by_month(callback.from_user.id, now.year, now.month)
    
    # Создаем словарь с данными по дням
    sessions_by_day = {}
    for session in sessions:
        day = session['start_time'].day
        if day not in sessions_by_day:
            sessions_by_day[day] = {
                'ratings': [],
                'count': 0,
                'total_duration': 0
            }
        sessions_by_day[day]['ratings'].append(session['rating'])
        sessions_by_day[day]['count'] += 1
        sessions_by_day[day]['total_duration'] += session['duration']
    
    # Вычисляем средние оценки
    for day, data in sessions_by_day.items():
        data['avg_rating'] = sum(data['ratings']) / len(data['ratings'])
    
    # Формируем текст
    text = "📅 *Календарь медитаций*\n\n"
    text += "🟢 8-10 баллов | 🟡 5-7 баллов | 🔴 1-4 балла\n"
    text += "_Цифра в скобках - количество медитаций за день_\n\n"
    
    # Статистика месяца
    if sessions:
        total_sessions = len(sessions)
        total_duration = sum(s['duration'] for s in sessions)
        avg_rating = sum(s['rating'] for s in sessions) / total_sessions
        days_with_practice = len(sessions_by_day)
        
        text += f"*Статистика {now.strftime('%B %Y')}:*\n"
        text += f"• Медитаций: {total_sessions}\n"
        text += f"• Дней с практикой: {days_with_practice}\n"
        text += f"• Общее время: {total_duration} мин\n"
        text += f"• Средняя оценка: {avg_rating:.1f}/10\n"
    
    keyboard = get_calendar_keyboard(now.year, now.month, sessions_by_day)
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

async def show_day_details(callback: types.CallbackQuery, db):
    """Показать детали медитаций за конкретный день"""
    _, _, year, month, day = callback.data.split("_")
    selected_date = date(int(year), int(month), int(day))
    
    stats = await db.get_daily_stats(callback.from_user.id, selected_date)
    
    if stats['sessions_count'] == 0:
        await callback.answer("В этот день не было медитаций", show_alert=True)
        return
    
    text = f"📅 *Медитации за {selected_date.strftime('%d.%m.%Y')}*\n\n"
    text += f"Всего сессий: {stats['sessions_count']}\n"
    text += f"Общее время: {stats['total_duration']} минут\n"
    text += f"Средняя оценка: {stats['avg_rating']:.1f}/10\n\n"
    
    for i, session in enumerate(stats['sessions'], 1):
        time = session['start_time'].strftime("%H:%M")
        text += f"*Сессия {i} ({time})*\n"
        text += f"⏱️ Продолжительность: {session['duration']} мин\n"
        text += f"⭐ Оценка: {session['rating']}/10\n"
        if session['comment']:
            text += f"💭 Комментарий: {session['comment']}\n"
        text += "\n"
    
    # Кнопка возврата к календарю
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к календарю", callback_data="show_calendar")
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

async def navigate_calendar(callback: types.CallbackQuery, db):
    """Навигация по месяцам календаря"""
    parts = callback.data.split("_")
    direction = parts[1]
    year = int(parts[2])
    month = int(parts[3])
    
    # Изменяем месяц
    if direction == "prev":
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    else:  # next
        month += 1
        if month > 12:
            month = 1
            year += 1
    
    # Получаем данные за новый месяц
    sessions = await db.get_sessions_by_month(callback.from_user.id, year, month)
    
    # Создаем словарь с данными по дням
    sessions_by_day = {}
    for session in sessions:
        day = session['start_time'].day
        if day not in sessions_by_day:
            sessions_by_day[day] = {
                'ratings': [],
                'count': 0,
                'total_duration': 0
            }
        sessions_by_day[day]['ratings'].append(session['rating'])
        sessions_by_day[day]['count'] += 1
        sessions_by_day[day]['total_duration'] += session['duration']
    
    # Вычисляем средние оценки
    for day, data in sessions_by_day.items():
        data['avg_rating'] = sum(data['ratings']) / len(data['ratings'])
    
    # Обновляем календарь
    month_names = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    
    text = f"📅 *Календарь медитаций - {month_names[month]} {year}*\n\n"
    text += "🟢 8-10 баллов | 🟡 5-7 баллов | 🔴 1-4 балла\n\n"
    
    if sessions:
        total_sessions = len(sessions)
        total_duration = sum(s['duration'] for s in sessions)
        avg_rating = sum(s['rating'] for s in sessions) / total_sessions
        days_with_practice = len(sessions_by_day)
        
        text += f"*Статистика месяца:*\n"
        text += f"• Медитаций: {total_sessions}\n"
        text += f"• Дней с практикой: {days_with_practice}\n"
        text += f"• Общее время: {total_duration} мин\n"
        text += f"• Средняя оценка: {avg_rating:.1f}/10\n"
    else:
        text += "В этом месяце медитаций не было\n"
    
    keyboard = get_calendar_keyboard(year, month, sessions_by_day)
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

async def show_week_history(callback: types.CallbackQuery, db):
    """Показать историю за неделю"""
    user_id = callback.from_user.id
    week_ago = datetime.now() - timedelta(days=7)
    
    # Получаем сессии за неделю
    sessions = await db.get_user_sessions(user_id, limit=50)  # Берем больше, потом отфильтруем
    week_sessions = [s for s in sessions if s['start_time'] >= week_ago]
    
    if not week_sessions:
        await callback.answer("За последнюю неделю не было медитаций", show_alert=True)
        return
    
    # Считаем статистику
    total_duration = sum(s['duration'] for s in week_sessions)
    avg_rating = sum(s['rating'] for s in week_sessions) / len(week_sessions)
    days_with_meditation = len(set(s['start_time'].date() for s in week_sessions))
    
    text = "📊 *Медитации за последнюю неделю*\n\n"
    text += f"📈 *Статистика:*\n"
    text += f"• Всего медитаций: {len(week_sessions)}\n"
    text += f"• Дней с практикой: {days_with_meditation}/7\n"
    text += f"• Общее время: {total_duration} минут\n"
    text += f"• Средняя оценка: {avg_rating:.1f}/10\n\n"
    
    text += "*Детали:*\n"
    for session in week_sessions[:10]:  # Показываем только 10 последних
        date = session['start_time'].strftime("%d.%m %H:%M")
        text += f"• {date} - {session['duration']} мин, ⭐ {session['rating']}/10\n"
    
    if len(week_sessions) > 10:
        text += f"\n_...и еще {len(week_sessions) - 10} медитаций_"
    
    # Кнопка возврата
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back_to_history")
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

async def back_to_history(callback: types.CallbackQuery, db):
    """Вернуться к истории медитаций"""
    # Получаем данные для истории
    user_id = callback.from_user.id
    sessions = await db.get_user_sessions(user_id, limit=15)
    
    if not sessions:
        await callback.message.edit_text("У вас пока нет завершенных медитаций.")
        await callback.answer()
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
                cut_pos = comment[:100].rfind(' ')
                if cut_pos > 80:
                    comment = comment[:cut_pos] + "..."
                else:
                    comment = comment[:100] + "..."
            text += f"   💭 {comment}\n"
        text += "\n"
    
    # Добавляем кнопки для дополнительных действий
    keyboard = get_history_keyboard()
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

async def ignore_callback(callback: types.CallbackQuery):
    """Игнорировать нажатия на неактивные кнопки календаря"""
    await callback.answer()
