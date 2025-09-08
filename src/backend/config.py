import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры пирамиды
# PAYOUT_PERCENT = 0.25 # Now managed in Redis
GROWTH_FACTOR = 2
MAX_LEVELS = 5
POWER_COST = 100
BASE_RETURN = 0.2
FAN_SPEED_BASE = 1
# LOTTERY_POOL = 0 # Now managed in Redis

# Redis Keys for global state
REDIS_KEY_PAYOUT_PERCENT = "pyramid:payout_percent"
REDIS_KEY_LOTTERY_POOL = "pyramid:lottery_pool"

# Telegram Bot Token (читается из .env)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
YOUR_ADMIN_ID = int(os.getenv('YOUR_ADMIN_ID', '123456789')) # Замени на свой Telegram user_id

# Redis и PostgreSQL (читаются из .env)
REDIS_URL = os.getenv('REDIS_URL', "redis://localhost")
POSTGRES_DSN = os.getenv('POSTGRES_DSN', "postgresql://user:pass@localhost/pyramid")

# Celery (читается из .env)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost')

# NowPayments (читается из .env)
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY', 'YOUR_API_KEY')

# Квесты
QUESTS = {
    "invite_2": {"task": "Пригласи 2 друзей", "reward": 0.1, "type": "return_boost"},
    "invest_500": {"task": "Вложи 500 USDToken", "reward": 1, "type": "power"},
    "level_up": {"task": "Поднимись на уровень", "reward": 50, "type": "usd"},
    "weekly_active": {"task": "Будь активен 7 дней", "reward": 0.2, "type": "fan_speed_bonus"}
}

# Достижения
ACHIEVEMENTS = {
    "first_million": {"task": "Достигни 1M USDToken", "reward": 0.5, "type": "power"},
    "referral_titan": {"task": "Пригласи 100 рефералов", "reward": 1000, "type": "usd"},
    "power_master": {"task": "Достигни 10 мощности", "reward": 500, "type": "usd"}
}

# Глобальные переменные для состояния (будут управляться в main или через Redis)
stability_data = []
event_active = False
event_end = None