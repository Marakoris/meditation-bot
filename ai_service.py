# .env.openrouter.example
# Пример конфигурации для OpenRouter

# Telegram Bot Token from @BotFather
BOT_TOKEN=your_bot_token_here

# Database URL (PostgreSQL)
DATABASE_URL=postgresql://meditation_user:meditation_pass@localhost:5432/meditation_bot

# OpenRouter Configuration
# Получите ключ на https://openrouter.ai/keys
AI_API_KEY=sk-or-v1-your_openrouter_key_here
AI_SERVICE=openrouter

# Выберите модель (необязательно, по умолчанию claude-3-haiku)
# Рекомендуемые модели:
# - anthropic/claude-3-haiku (быстрый, $0.25/$1.25 за 1M токенов)
# - anthropic/claude-3-sonnet (умный, $3/$15 за 1M токенов)
# - openai/gpt-3.5-turbo (дешевый, $0.50/$1.50 за 1M токенов)
# - openai/gpt-4-turbo (мощный, $10/$30 за 1M токенов)
# - google/gemini-pro (есть бесплатный лимит)
# - meta-llama/llama-3-8b-instruct (очень дешевый, $0.05/$0.10 за 1M токенов)
# - mistralai/mistral-7b-instruct (дешевый, $0.07/$0.07 за 1M токенов)
AI_MODEL=anthropic/claude-3-haiku

# Admin Telegram IDs (comma-separated)
ADMIN_IDS=123456789,987654321

# Optional settings
TIMEZONE=Europe/Moscow
MAX_SESSIONS_PER_DAY=10
