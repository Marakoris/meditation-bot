#!/bin/bash
# quick_install.sh - Быстрая установка Meditation Bot с исправлениями

echo "🧘 Быстрая установка Meditation Bot"
echo "====================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_step() {
    echo -e "\n${GREEN}➤ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт с правами root: sudo $0"
    exit 1
fi

# Переменные
BOT_DIR="/root/meditation_bot"
VENV_DIR="$BOT_DIR/meditation_bot_env"
SERVICE_NAME="meditation-bot"

print_step "1. Остановка существующего сервиса (если есть)"
systemctl stop $SERVICE_NAME 2>/dev/null || true

print_step "2. Создание директории проекта"
mkdir -p $BOT_DIR
cd $BOT_DIR

print_step "3. Создание виртуального окружения Python"
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

print_step "4. Обновление pip и установка зависимостей"
pip install --upgrade pip
pip install aiogram==3.3.0 asyncpg==0.29.0 aiohttp==3.9.1 python-dotenv==1.0.0 pytz==2024.1

print_step "5. Создание requirements.txt"
cat > $BOT_DIR/requirements.txt << 'EOF'
aiogram==3.3.0
asyncpg==0.29.0
aiohttp==3.9.1
python-dotenv==1.0.0
pytz==2024.1
EOF

print_step "6. Настройка PostgreSQL"
if ! command -v psql &> /dev/null; then
    print_info "Установка PostgreSQL..."
    apt update
    apt install -y postgresql postgresql-contrib
    systemctl start postgresql
    systemctl enable postgresql
else
    print_info "PostgreSQL уже установлен"
fi

# Создание пользователя и базы данных
print_info "Создание базы данных meditation_bot..."
sudo -u postgres psql << 'EOF'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'meditation_user') THEN
        CREATE USER meditation_user WITH PASSWORD 'Med1tat10n_2024!';
    END IF;
END
$$;

DROP DATABASE IF EXISTS meditation_bot;
CREATE DATABASE meditation_bot OWNER meditation_user;
GRANT ALL PRIVILEGES ON DATABASE meditation_bot TO meditation_user;
\q
EOF

print_step "7. Создание файла конфигурации (.env)"
cat > $BOT_DIR/.env << 'EOF'
# Telegram Bot Token - ПОЛУЧИТЕ У @BotFather
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Database (обычно не нужно менять)
DATABASE_URL=postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot

# AI Service - ПОЛУЧИТЕ КЛЮЧ НА https://openrouter.ai/keys
AI_API_KEY=YOUR_AI_API_KEY_HERE
AI_SERVICE=openrouter
AI_MODEL=anthropic/claude-3-haiku

# Admin Telegram IDs - ВАШИ ID (узнать у @userinfobot)
ADMIN_IDS=YOUR_TELEGRAM_ID_HERE

# Settings
TIMEZONE=Europe/Moscow
MAX_SESSIONS_PER_DAY=10
EOF

print_step "8. Создание исправленного config.py"
cat > $BOT_DIR/config.py << 'EOF'
# config.py
from dotenv import load_dotenv
load_dotenv()

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Config:
    """Конфигурация приложения"""
    
    # Bot
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    
    # Database
    DATABASE_URL: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", 
        "postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot"
    ))
    
    # AI Service
    AI_API_KEY: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    AI_SERVICE: str = field(default_factory=lambda: os.getenv("AI_SERVICE", "openrouter"))
    AI_MODEL: str = field(default_factory=lambda: os.getenv("AI_MODEL", "anthropic/claude-3-haiku"))
    
    # Admin IDs
    ADMIN_IDS: list[int] = field(default_factory=lambda: [
        int(id.strip()) 
        for id in os.getenv("ADMIN_IDS", "").split(",") 
        if id.strip()
    ])
    
    # Optional settings
    TIMEZONE: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Moscow"))
    MAX_SESSIONS_PER_DAY: int = field(default_factory=lambda: int(os.getenv("MAX_SESSIONS_PER_DAY", "10")))
    
    def __post_init__(self):
        """Валидация конфигурации"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not self.AI_API_KEY:
            raise ValueError("AI_API_KEY is required")
        
        # Преобразуем DATABASE_URL для asyncpg если нужно
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql://", 1
            )
EOF

print_step "9. Создание папки для обработчиков"
mkdir -p $BOT_DIR/handlers
touch $BOT_DIR/handlers/__init__.py

print_step "10. Создание systemd сервиса"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Meditation Telegram Bot
After=network.target postgresql.service
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BOT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/python bot.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

print_step "11. Создание скрипта управления"
cat > $BOT_DIR/manage.sh << 'EOF'
#!/bin/bash
# Управление Meditation Bot

SERVICE="meditation-bot"
BOT_DIR="/root/meditation_bot"
VENV_DIR="$BOT_DIR/meditation_bot_env"

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

case "$1" in
    start)
        echo -e "${GREEN}🚀 Запуск бота...${NC}"
        systemctl start $SERVICE
        sleep 2
        systemctl status $SERVICE --no-pager
        ;;
    stop)
        echo -e "${YELLOW}⏹️ Остановка бота...${NC}"
        systemctl stop $SERVICE
        ;;
    restart)
        echo -e "${YELLOW}🔄 Перезапуск бота...${NC}"
        systemctl restart $SERVICE
        sleep 2
        systemctl status $SERVICE --no-pager
        ;;
    status)
        systemctl status $SERVICE
        ;;
    logs)
        echo -e "${GREEN}📋 Логи бота (Ctrl+C для выхода):${NC}"
        journalctl -u $SERVICE -f
        ;;
    test)
        echo -e "${YELLOW}🧪 Тестовый запуск...${NC}"
        cd $BOT_DIR
        source $VENV_DIR/bin/activate
        python config.py && echo "✅ Конфигурация OK" || echo "❌ Ошибка конфигурации"
        ;;
    check)
        echo -e "${GREEN}🔍 Проверка файлов...${NC}"
        echo "Проверяем основные файлы:"
        [ -f "$BOT_DIR/bot.py" ] && echo "✅ bot.py" || echo "❌ bot.py отсутствует"
        [ -f "$BOT_DIR/config.py" ] && echo "✅ config.py" || echo "❌ config.py отсутствует"
        [ -f "$BOT_DIR/.env" ] && echo "✅ .env" || echo "❌ .env отсутствует"
        [ -d "$VENV_DIR" ] && echo "✅ venv" || echo "❌ venv отсутствует"
        echo ""
        echo "Проверяем конфигурацию:"
        cd $BOT_DIR
        source $VENV_DIR/bin/activate
        python -c "from config import Config; c=Config(); print('BOT_TOKEN:', 'OK' if c.BOT_TOKEN else 'НЕ ЗАДАН')"
        python -c "from config import Config; c=Config(); print('AI_API_KEY:', 'OK' if c.AI_API_KEY else 'НЕ ЗАДАН')"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|test|check}"
        echo ""
        echo "  start    - Запустить бота"
        echo "  stop     - Остановить бота"
        echo "  restart  - Перезапустить бота"
        echo "  status   - Проверить статус"
        echo "  logs     - Смотреть логи в реальном времени"
        echo "  test     - Тестовая проверка конфигурации"
        echo "  check    - Проверить наличие всех файлов"
        exit 1
        ;;
esac
EOF

chmod +x $BOT_DIR/manage.sh

print_step "12. Активация сервиса"
systemctl daemon-reload
systemctl enable $SERVICE_NAME

print_step "✅ Базовая установка завершена!"

echo ""
echo -e "${YELLOW}📋 ЧТО НУЖНО СДЕЛАТЬ ДАЛЕЕ:${NC}"
echo ""
echo "1. ${GREEN}Скопируйте файлы бота в $BOT_DIR:${NC}"
echo "   Нужны файлы: bot.py, database.py, keyboards.py, ai_service.py"
echo "   states.py, prompts.py, utils.py и папка handlers/"
echo ""
echo "2. ${GREEN}Настройте конфигурацию:${NC}"
echo "   nano $BOT_DIR/.env"
echo "   - Добавьте BOT_TOKEN от @BotFather"
echo "   - Добавьте AI_API_KEY (получить на https://openrouter.ai/keys)"
echo "   - Добавьте ADMIN_IDS (узнать у @userinfobot)"
echo ""
echo "3. ${GREEN}Проверьте файлы:${NC}"
echo "   $BOT_DIR/manage.sh check"
echo ""
echo "4. ${GREEN}Запустите бота:${NC}"
echo "   $BOT_DIR/manage.sh start"
echo ""
echo "5. ${GREEN}Проверьте логи:${NC}"
echo "   $BOT_DIR/manage.sh logs"
echo ""
echo -e "${BLUE}📁 Структура проекта:${NC}"
echo "$BOT_DIR/"
echo "├── meditation_bot_env/  # Виртуальное окружение"
echo "├── bot.py              # Основной файл (НУЖНО СКОПИРОВАТЬ)"
echo "├── config.py           # ✅ Создан"
echo "├── database.py         # База данных (НУЖНО СКОПИРОВАТЬ)"
echo "├── keyboards.py        # Клавиатуры (НУЖНО СКОПИРОВАТЬ)"
echo "├── ai_service.py       # AI сервис (НУЖНО СКОПИРОВАТЬ)"
echo "├── states.py           # Состояния FSM (НУЖНО СКОПИРОВАТЬ)"
echo "├── prompts.py          # AI промпты (НУЖНО СКОПИРОВАТЬ)"
echo "├── utils.py            # Утилиты (НУЖНО СКОПИРОВАТЬ)"
echo "├── handlers/           # Обработчики (НУЖНО СКОПИРОВАТЬ)"
echo "├── .env                # ✅ Создан (НУЖНО НАСТРОИТЬ)"
echo "├── requirements.txt    # ✅ Создан"
echo "└── manage.sh           # ✅ Создан"
echo ""
echo -e "${GREEN}🎯 После копирования файлов и настройки .env запустите:${NC}"
echo "   $BOT_DIR/manage.sh start"
