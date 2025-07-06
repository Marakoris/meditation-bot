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
