# 🚀 Руководство по развертыванию Meditation Bot

## 📋 Краткий обзор

Meditation Bot - это Telegram бот для отслеживания медитаций с AI-ассистентом, поддержкой марафонов и персонализированной обратной связью.

### ✨ Основные возможности:
- 🧘 Отслеживание медитаций с таймером
- 🤖 AI-ассистент для диалогов о медитации
- 📝 Ручная запись медитаций через естественный язык
- 🏃 Система марафонов с групповой статистикой
- 📊 Детальная аналитика и визуальный календарь
- 🗑️ Удаление ошибочных записей

## 🔧 Системные требования

- **OS**: Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- **Python**: 3.11+
- **RAM**: минимум 1GB
- **Storage**: минимум 2GB свободного места
- **PostgreSQL**: 13+

## 🚀 Быстрая установка

### Вариант 1: Автоматический скрипт (Рекомендуется)

```bash
# Скачайте и запустите скрипт установки
wget https://raw.githubusercontent.com/your-repo/meditation-bot/main/quick_install.sh
chmod +x quick_install.sh
sudo ./quick_install.sh
```

### Вариант 2: Ручная установка

#### 1. Подготовка системы
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git
```

#### 2. Настройка PostgreSQL
```bash
# Запуск PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создание пользователя и базы данных
sudo -u postgres psql << EOF
CREATE USER meditation_user WITH PASSWORD 'Med1tat10n_2024!';
CREATE DATABASE meditation_bot OWNER meditation_user;
GRANT ALL PRIVILEGES ON DATABASE meditation_bot TO meditation_user;
\q
EOF
```

#### 3. Настройка проекта
```bash
# Создание директории
sudo mkdir -p /root/meditation_bot
cd /root/meditation_bot

# Создание виртуального окружения
python3 -m venv meditation_bot_env
source meditation_bot_env/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install aiogram==3.3.0 asyncpg==0.29.0 aiohttp==3.9.1 python-dotenv==1.0.0 pytz==2024.1
```

#### 4. Копирование файлов проекта
```bash
# Скопируйте все файлы проекта в /root/meditation_bot/
# Обязательные файлы:
# - bot.py (основной файл)
# - config.py (конфигурация)
# - database.py (работа с БД)
# - keyboards.py (клавиатуры)
# - ai_service.py (AI интеграция)
# - states.py (состояния FSM)
# - prompts.py (AI промпты)
# - utils.py (утилиты)
# - handlers/ (папка с обработчиками)
```

#### 5. Настройка конфигурации
```bash
# Создание .env файла
nano /root/meditation_bot/.env
```

Добавьте в `.env`:
```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz123456789

# Database
DATABASE_URL=postgresql://meditation_user:Med1tat10n_2024!@localhost:5432/meditation_bot

# AI Service (получить на https://openrouter.ai/keys)
AI_API_KEY=sk-or-v1-ваш_ключ_openrouter
AI_SERVICE=openrouter
AI_MODEL=anthropic/claude-3-haiku

# Admin IDs (узнать у @userinfobot)
ADMIN_IDS=123456789,987654321

# Settings
TIMEZONE=Europe/Moscow
MAX_SESSIONS_PER_DAY=10
```

#### 6. Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/meditation-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=Meditation Telegram Bot
After=network.target postgresql.service
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/meditation_bot
Environment=PATH=/root/meditation_bot/meditation_bot_env/bin
ExecStart=/root/meditation_bot/meditation_bot_env/bin/python bot.py
Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=meditation-bot

[Install]
WantedBy=multi-user.target
```

#### 7. Запуск бота
```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable meditation-bot
sudo systemctl start meditation-bot

# Проверка статуса
sudo systemctl status meditation-bot

# Просмотр логов
journalctl -u meditation-bot -f
```

## 🔑 Получение необходимых ключей

### 1. Telegram Bot Token
1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 2. AI API Key (OpenRouter)
1. Зарегистрируйтесь на [OpenRouter.ai](https://openrouter.ai)
2. Перейдите в [Keys](https://openrouter.ai/keys)
3. Создайте новый API ключ
4. Пополните баланс ($5-10 хватит надолго)

### 3. Telegram ID администратора
1. Напишите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Скопируйте ваш User ID

## 🛠️ Управление ботом

### Команды systemctl
```bash
# Запуск
sudo systemctl start meditation-bot

# Остановка
sudo systemctl stop meditation-bot

# Перезапуск
sudo systemctl restart meditation-bot

# Статус
sudo systemctl status meditation-bot

# Логи
journalctl -u meditation-bot -f
```

### Скрипт управления (если установлен)
```bash
# Все команды управления
/root/meditation_bot/manage.sh start    # Запуск
/root/meditation_bot/manage.sh stop     # Остановка
/root/meditation_bot/manage.sh restart  # Перезапуск
/root/meditation_bot/manage.sh status   # Статус
/root/meditation_bot/manage.sh logs     # Логи
/root/meditation_bot/manage.sh check    # Проверка файлов
/root/meditation_bot/manage.sh test     # Тест конфигурации
```

## 🐛 Решение проблем

### Бот не запускается

#### 1. Проверьте конфигурацию
```bash
cd /root/meditation_bot
source meditation_bot_env/bin/activate
python -c "from config import Config; print('OK')"
```

#### 2. Проверьте .env файл
```bash
cat /root/meditation_bot/.env
# Убедитесь, что BOT_TOKEN и AI_API_KEY заполнены
```

#### 3. Проверьте логи
```bash
journalctl -u meditation-bot -n 50
```

### Ошибки "BOT_TOKEN is required"

**Проблема**: В config.py отсутствует загрузка .env файла

**Решение**:
```bash
# Проверьте, что в начале config.py есть:
head -n 5 /root/meditation_bot/config.py
# Должно быть:
# from dotenv import load_dotenv
# load_dotenv()
```

### Ошибки базы данных

#### 1. PostgreSQL не запущен
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 2. Проблемы с подключением
```bash
# Проверьте подключение
sudo -u postgres psql -c "\l" | grep meditation_bot
```

#### 3. Пересоздание базы данных
```bash
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS meditation_bot;
CREATE DATABASE meditation_bot OWNER meditation_user;
GRANT ALL PRIVILEGES ON DATABASE meditation_bot TO meditation_user;
\q
EOF
```

### Ошибки AI сервиса

#### 1. Неверный API ключ
```bash
# Проверьте ключ OpenRouter
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://openrouter.ai/api/v1/models
```

#### 2. Недостаточно средств на балансе
- Проверьте баланс на [OpenRouter.ai](https://openrouter.ai/credits)
- Пополните баланс при необходимости

## 📊 Мониторинг и обслуживание

### Проверка работоспособности
```bash
# Проверка статуса сервиса
systemctl is-active meditation-bot

# Проверка использования ресурсов
ps aux | grep meditation-bot
```

### Резервное копирование базы данных
```bash
# Создание бэкапа
sudo -u postgres pg_dump meditation_bot > /backup/meditation_bot_$(date +%Y%m%d).sql

# Восстановление из бэкапа
sudo -u postgres psql meditation_bot < /backup/meditation_bot_20250101.sql
```

### Логротация
```bash
# Настройка автоматической очистки логов
sudo journalctl --vacuum-time=30d
sudo journalctl --vacuum-size=100M
```

### Обновление кода
```bash
# Остановка бота
sudo systemctl stop meditation-bot

# Обновление файлов (git pull или копирование новых файлов)
cd /root/meditation_bot
# ... обновление файлов ...

# Обновление зависимостей при необходимости
source meditation_bot_env/bin/activate
pip install -r requirements.txt

# Перезапуск
sudo systemctl start meditation-bot
```

## 🔐 Безопасность

### Рекомендации по безопасности
1. **Не делитесь токенами**: Никогда не публикуйте BOT_TOKEN и AI_API_KEY
2. **Ограничьте SSH доступ**: Используйте ключи вместо паролей
3. **Обновляйте систему**: Регулярно устанавливайте обновления
4. **Мониторинг логов**: Следите за подозрительной активностью
5. **Резервное копирование**: Регулярно создавайте бэкапы данных

### Базовая настройка файрвола
```bash
# Установка ufw
sudo apt install ufw

# Разрешение SSH и HTTP/HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Включение файрвола
sudo ufw enable
```

## 📞 Поддержка

### Полезные ссылки
- **Документация Aiogram**: https://docs.aiogram.dev/
- **OpenRouter документация**: https://openrouter.ai/docs
- **PostgreSQL документация**: https://www.postgresql.org/docs/

### Частые вопросы

**Q: Бот не отвечает на сообщения**
A: Проверьте статус сервиса и логи. Убедитесь, что токен бота правильный.

**Q: AI не генерирует ответы**
A: Проверьте AI_API_KEY и баланс на OpenRouter.ai

**Q: Медитации не сохраняются**
A: Проверьте подключение к PostgreSQL и права доступа к базе данных.

**Q: Как изменить модель AI?**
A: Измените параметр AI_MODEL в .env файле и перезапустите бота.

---

**Создано с ❤️ для практикующих медитацию**
