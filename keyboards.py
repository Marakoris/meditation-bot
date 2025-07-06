# keyboards.py
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard(meditation_active: bool = False, is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    """Главная клавиатура бота"""
    builder = ReplyKeyboardBuilder()
    
    if meditation_active:
        builder.button(text="⏹️ Завершить медитацию")
    else:
        builder.button(text="🧘 Начать медитацию")
    
    builder.button(text="🏃 Присоединиться к марафону")
    builder.button(text="📊 Мой прогресс")
    builder.button(text="📖 История медитаций")
    
    if is_admin:
        builder.button(text="👨‍💼 Создать марафон")
    
    builder.adjust(2, 2, 1)
    
    return builder.as_markup(resize_keyboard=True)

def get_rating_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для оценки медитации"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки от 1 до 10
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"rating_{i}")
    
    # Размещаем по 5 кнопок в ряд
    builder.adjust(5, 5)
    
    return builder.as_markup()

def get_cancel_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отменить")
    return builder.as_markup(resize_keyboard=True)

def get_marathon_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура администратора марафона"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📊 Статистика марафона", callback_data="marathon_stats")
    builder.button(text="📋 Список участников", callback_data="marathon_participants")
    builder.button(text="📢 Отправить сообщение", callback_data="marathon_broadcast")
    builder.button(text="🏁 Завершить марафон", callback_data="marathon_finish")
    
    builder.adjust(2, 2)
    
    return builder.as_markup()

def get_confirmation_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Да", callback_data="confirm_yes")
    builder.button(text="❌ Нет", callback_data="confirm_no")
    
    builder.adjust(2)
    
    return builder.as_markup()

def get_history_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для истории медитаций"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Календарь", callback_data="show_calendar")
    builder.button(text="📊 За неделю", callback_data="history_week")
    builder.button(text="📈 За месяц", callback_data="history_month")
    
    builder.adjust(3)
    
    return builder.as_markup()

def get_calendar_keyboard(year: int, month: int) -> types.InlineKeyboardMarkup:
    """Клавиатура календаря"""
    from calendar import monthrange, month_name
    import locale
    
    # Устанавливаем русскую локаль для названий месяцев
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except:
        pass
    
    builder = InlineKeyboardBuilder()
    
    # Заголовок с месяцем и годом
    month_name_ru = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    
    # Навигация по месяцам
    builder.button(text="◀️", callback_data=f"cal_prev_{year}_{month}")
    builder.button(text=f"{month_name_ru[month]} {year}", callback_data="cal_ignore")
    builder.button(text="▶️", callback_data=f"cal_next_{year}_{month}")
    builder.adjust(3)
    
    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days:
        builder.button(text=day, callback_data="cal_ignore")
    builder.adjust(3, 7)
    
    # Получаем первый день месяца и количество дней
    first_day, days_in_month = monthrange(year, month)
    
    # Добавляем пустые кнопки до первого дня
    for _ in range(first_day):
        builder.button(text=" ", callback_data="cal_ignore")
    
    # Добавляем дни месяца
    for day in range(1, days_in_month + 1):
        builder.button(text=str(day), callback_data=f"cal_day_{year}_{month}_{day}")
    
    # Выравниваем сетку
    total_buttons = 3 + 7 + first_day + days_in_month
    rows = [3, 7] + [7] * ((total_buttons - 10 + 6) // 7)
    builder.adjust(*rows)
    
    return builder.as_markup()
