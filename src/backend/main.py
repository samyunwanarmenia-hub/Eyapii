import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from celery import Celery

# Импорт конфигурации
from src.backend.config import (
    logger, TELEGRAM_BOT_TOKEN, CELERY_BROKER_URL, POSTGRES_DSN,
    YOUR_ADMIN_ID, REDIS_KEY_LOTTERY_POOL, REDIS_KEY_PAYOUT_PERCENT
)

# Импорт метрик
from src.backend.metrics import request_duration

# Импорт модулей базы данных
from src.backend.database import (
    init_db_pool, init_sqlite_db, pool, redis, cache_referral_tree, get_user,
    set_payout_percent, get_payout_percent, get_lottery_pool, update_lottery_pool
)

# Импорт модулей ML
from src.backend.ml_models import EventOptimizer

# Импорт игровой логики
from src.backend.game_logic import get_rank

# Импорт запланированных задач
from src.backend.scheduled_tasks import (
    update_fan_profits_task, optimize_payout_dynamic, advanced_analyze,
    detect_anomalies, circuit_breaker, auto_events, retention_bonus, backup_db,
    event_active, event_end, stability_data, event_optimizer
)

# Импорт API обработчиков
from src.backend.api_handlers import get_user_data_api, check_transaction_limit_api
from src.backend.payment_handlers import create_payment_api # Import the new payment handler

# Импорт Telegram обработчиков из нового пакета
from src.backend.telegram_handlers import (
    start, button, join, vote, buy_power, daily, lottery, withdraw, admin,
    dashboard, status, leaderboard
)

# Celery для очередей
celery = Celery('pyramid', broker=CELERY_BROKER_URL)

# Глобальный объект приложения Telegram (будет инициализирован в main)
app_telegram = None

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get('/api/user/{user_id}', get_user_data_api)
    app_web.router.add_get('/api/check_transaction_limit/{user_id}', check_transaction_limit_api)
    app_web.router.add_post('/api/create_payment', create_payment_api) # Add the new payment route
    # Добавляем CORS для разработки
    cors = web.middleware.cors.cors_middleware(
        allow_headers="*",
        allow_methods="*",
        allow_credentials=True,
        expose_headers="*",
    )
    app_web.middlewares.append(cors)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    logger.info("Web server started on http://localhost:8080")

async def main():
    global pool, app_telegram
    
    # Инициализация баз данных
    pool = await init_db_pool()
    init_sqlite_db()

    # Инициализация глобальных переменных в Redis, если они не установлены
    if not await redis.exists(REDIS_KEY_PAYOUT_PERCENT):
        await set_payout_percent(0.25) # Default value
    if not await redis.exists(REDIS_KEY_LOTTERY_POOL):
        await update_lottery_pool(0.0) # Default value

    # Инициализация Telegram бота
    app_telegram = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("join", join))
    app_telegram.add_handler(CommandHandler("buy_power", buy_power))
    app_telegram.add_handler(CommandHandler("status", status))
    app_telegram.add_handler(CommandHandler("leaderboard", leaderboard))
    app_telegram.add_handler(CommandHandler("vote", vote))
    app_telegram.add_handler(CommandHandler("daily", daily))
    app_telegram.add_handler(CommandHandler("lottery", lottery))
    app_telegram.add_handler(CommandHandler("withdraw", withdraw))
    app_telegram.add_handler(CommandHandler("admin", admin))
    app_telegram.add_handler(CommandHandler("dashboard", dashboard))
    app_telegram.add_handler(CallbackQueryHandler(button))
    
    # Инициализация планировщика задач
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_fan_profits_task, 'interval', seconds=10)
    scheduler.add_job(optimize_payout_dynamic, 'interval', hours=24)
    scheduler.add_job(advanced_analyze, 'interval', hours=24, args=[app_telegram]) # Передаем app_telegram
    scheduler.add_job(detect_anomalies, 'interval', hours=12)
    scheduler.add_job(circuit_breaker, 'interval', hours=1)
    scheduler.add_job(auto_events, 'interval', hours=6, args=[app_telegram]) # Передаем app_telegram
    scheduler.add_job(retention_bonus, 'interval', hours=24, args=[app_telegram]) # Передаем app_telegram
    scheduler.add_job(backup_db, 'interval', hours=24)
    scheduler.add_job(cache_referral_tree, 'interval', hours=1, args=[get_user]) # Передаем get_user
    # scheduler.add_job(finalize_dao, 'interval', weeks=1) # Removed
    scheduler.start()
    
    # Запускаем веб-сервер как фоновую задачу
    asyncio.create_task(start_web_server())
    # asyncio.create_task(listen_for_events()) # Removed
    
    logger.info("Pyramid Wealth Application started!")
    await app_telegram.run_polling()

if __name__ == '__main__':
    asyncio.run(main())