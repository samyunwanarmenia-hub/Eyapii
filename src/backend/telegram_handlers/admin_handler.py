import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger, YOUR_ADMIN_ID
from src.backend.database import pool, get_payout_percent, get_lottery_pool
from src.backend.metrics import request_duration

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        if user_id != YOUR_ADMIN_ID:
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                "Доступ запрещён! 😡"
            )
            return
        async with pool.acquire() as conn:
            total_users = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i}') for i in range(10)])
            total_invested = sum([await conn.fetchval(f'SELECT SUM(investment) FROM users_shard_{i}') or 0 for i in range(10)])
            total_paid_out = await conn.fetchval('SELECT SUM(amount) FROM transactions WHERE type = "withdraw"') or 0
            active_users = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i} WHERE (julianday("now") - julianday(last_update)) <= 7') for i in range(10)])
        stability = total_invested / max(1, total_paid_out)
        payout_percent = await get_payout_percent() # Get from Redis
        lottery_pool_amount = await get_lottery_pool() # Get from Redis
        output = (
            f"📊 Админ-панель Пирамиды Богатства 📊\n"
            f"Всего пользователей: {total_users}\n"
            f"Активные пользователи: {active_users}\n"
            f"Общие вложения: {total_invested:.2f} USDToken\n"
            f"Общие выплаты: {total_paid_out:.2f} USDToken\n"
            f"Стабильность: {stability:.2f}\n"
            f"Процент выплат: {payout_percent*100:.2f}%\n"
            f"Призовой фонд лотереи: {lottery_pool_amount:.2f} USDToken"
        )
        await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(output)