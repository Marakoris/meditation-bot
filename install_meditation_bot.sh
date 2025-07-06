#!/bin/bash
# install_meditation_bot.sh - Установка Meditation Bot как у других ботов

echo "🧘 Установка Meditation Bot"
echo "=========================="

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Переменные
BOT_DIR="/root/meditation_bot"
VENV_DIR="$BOT_DIR/meditation_bot_env"
SERVICE_NAME="meditation-bot"

# 1. Создание директории
echo -e "\n${GREEN}1. Создание директории бота...${NC}"
mkdir -p $BOT_DIR
cd $BOT_DIR

# 2. Создание виртуального окружения
echo -e "\n${GREEN}2. Создание виртуального окружения...${NC}"
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 3. Обновление pip и установка зависимостей
echo -e "\n${GREEN}3. Установка зависимостей...${NC}"
pip install --upgrade pip
pip install aiogram==3.3.0 asyncpg==0.29.0 aiohttp==3.9.1 python-dotenv==1.0.0 pytz==2024.1

# 4. Установка PostgreSQL если нужно
echo -e "\n${GREEN}4. Проверка PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo "Установка PostgreSQL..."
    apt update
    apt install -y postgresql postgresql-contrib
    systemctl start postgresql
    systemctl enable postgresql
else
    echo -e "${YELLOW}PostgreSQL уже установлен${NC}"
fi

# 5. Создание базы данных
echo -e "\n${GREEN}5. Настройка базы данных...${NC}"
sudo -u postgres psql << EOF
-- Создаем пользователя и базу если не существуют
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'meditation_user') THEN
        CREATE USER meditation_user WITH PASSWORD 'Med1tat10n_2024!';
    END IF;
END
\$\$;

CREATE DATABASE meditation_bot OWNER meditation_user;
GRANT ALL PRIVILEGES ON DATABASE meditation_bot TO meditation_user;
\q
EOF
echo -e "${GREEN}✓ База данных настроена${NC}"

# 6. Создание конфигурационных файлов
echo -e "\n${GREEN}6. Создание конфигурации...${NC}"

# .env файл
cat > $BOT_DIR/.env << 'EOF'
# Telegram Bot Token - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Database
DATABASE_URL=postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot

# AI Service - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
AI_API_KEY=YOUR_AI_API_KEY_HERE
AI_SERVICE=claude  # или openai

# Admin Telegram IDs (через запятую)
ADMIN_IDS=

# Settings
TIMEZONE=Europe/Moscow
MAX_SESSIONS_PER_DAY=10
EOF

# config.py для импорта (на случай если забудете скопировать основной)
cat > $BOT_DIR/config_example.py << 'EOF'
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_SERVICE: str = os.getenv("AI_SERVICE", "claude")
    ADMIN_IDS: list[int] = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    MAX_SESSIONS_PER_DAY: int = int(os.getenv("MAX_SESSIONS_PER_DAY", "10"))
EOF

# 7. Создание systemd сервиса
echo -e "\n${GREEN}7. Создание systemd сервиса...${NC}"
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

# 8. Создание скрипта управления
cat > $BOT_DIR/manage.sh << 'EOF'
#!/bin/bash
# Управление Meditation Bot

SERVICE="meditation-bot"
BOT_DIR="/root/meditation_bot"
VENV_DIR="$BOT_DIR/meditation_bot_env"

case "$1" in
    start)
        echo "🚀 Запуск бота..."
        systemctl start $SERVICE
        sleep 2
        systemctl status $SERVICE --no-pager
        ;;
    stop)
        echo "⏹️ Остановка бота..."
        systemctl stop $SERVICE
        ;;
    restart)
        echo "🔄 Перезапуск бота..."
        systemctl restart $SERVICE
        sleep 2
        systemctl status $SERVICE --no-pager
        ;;
    status)
        systemctl status $SERVICE
        ;;
    logs)
        echo "📋 Логи бота (Ctrl+C для выхода):"
        journalctl -u $SERVICE -f
        ;;
    install-deps)
        echo "📦 Установка/обновление зависимостей..."
        cd $BOT_DIR
        source $VENV_DIR/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
        ;;
    test)
        echo "🧪 Тестовый запуск бота..."
        cd $BOT_DIR
        source $VENV_DIR/bin/activate
        python bot.py
        ;;
    env)
        echo "🔧 Активация виртуального окружения..."
        echo "Выполните: source $VENV_DIR/bin/activate"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|install-deps|test|env}"
        echo ""
        echo "  start        - Запустить бота"
        echo "  stop         - Остановить бота"
        echo "  restart      - Перезапустить бота"
        echo "  status       - Проверить статус"
        echo "  logs         - Смотреть логи в реальном времени"
        echo "  install-deps - Установить/обновить зависимости"
        echo "  test         - Тестовый запуск (не через systemd)"
        echo "  env          - Показать команду активации venv"
        exit 1
        ;;
esac
EOF

chmod +x $BOT_DIR/manage.sh

# 9. Создание requirements.txt
cat > $BOT_DIR/requirements.txt << 'EOF'
aiogram==3.3.0
asyncpg==0.29.0
aiohttp==3.9.1
python-dotenv==1.0.0
pytz==2024.1
EOF

# 10. Инструкции по завершению установки
echo -e "\n${GREEN}✅ Установка почти завершена!${NC}"
echo -e "\n${YELLOW}⚠️ ВАЖНО! Осталось сделать:${NC}"
echo ""
echo "1. Скопируйте файлы бота в $BOT_DIR:"
echo "   Вам нужны файлы: bot.py, config.py, database.py, keyboards.py, ai_service.py, utils.py"
echo ""
echo "   Если файлы на вашем компьютере:"
echo "   ${GREEN}scp bot.py config.py database.py keyboards.py ai_service.py utils.py root@$(hostname -I | awk '{print $1}'):$BOT_DIR/${NC}"
echo ""
echo "2. Настройте конфигурацию:"
echo "   ${GREEN}nano $BOT_DIR/.env${NC}"
echo "   - Добавьте BOT_TOKEN от @BotFather"
echo "   - Добавьте AI_API_KEY (Claude или OpenAI)"
echo "   - Добавьте ADMIN_IDS (ваш Telegram ID)"
echo ""
echo "3. Активируйте сервис:"
echo "   ${GREEN}systemctl daemon-reload${NC}"
echo "   ${GREEN}systemctl enable $SERVICE_NAME${NC}"
echo ""
echo "4. Запустите бота:"
echo "   ${GREEN}systemctl start $SERVICE_NAME${NC}"
echo "   или"
echo "   ${GREEN}$BOT_DIR/manage.sh start${NC}"
echo ""
echo "5. Проверьте статус:"
echo "   ${GREEN}$BOT_DIR/manage.sh status${NC}"
echo "   ${GREEN}$BOT_DIR/manage.sh logs${NC}"
echo ""
echo -e "${GREEN}📁 Структура проекта:${NC}"
echo "$BOT_DIR/"
echo "├── meditation_bot_env/    # Виртуальное окружение"
echo "├── bot.py                 # Основной файл"
echo "├── config.py              # Конфигурация"
echo "├── database.py            # База данных"
echo "├── keyboards.py           # Клавиатуры"
echo "├── ai_service.py          # ИИ сервис"
echo "├── utils.py               # Утилиты"
echo "├── .env                   # Переменные окружения"
echo "├── requirements.txt       # Зависимости"
echo "└── manage.sh              # Скрипт управления"
echo ""
echo -e "${GREEN}🗄️ База данных PostgreSQL:${NC}"
echo "Database: meditation_bot"
echo "User: meditation_user"
echo "Password: Med1tat10n_2024!"
echo ""
echo -e "${YELLOW}💡 Полезные команды:${NC}"
echo "$BOT_DIR/manage.sh start    # Запустить"
echo "$BOT_DIR/manage.sh stop     # Остановить"
echo "$BOT_DIR/manage.sh restart  # Перезапустить"
echo "$BOT_DIR/manage.sh logs     # Смотреть логи"
echo "$BOT_DIR/manage.sh test     # Тестовый запуск"
