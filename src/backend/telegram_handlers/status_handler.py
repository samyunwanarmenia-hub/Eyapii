import asyncio
import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger
from src.backend.database import pool, get_user, update_user, redis, get_payout_percent
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.metrics import request_duration
from src.backend.scheduled_tasks import event_active, event_end

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        async with pool.acquire() as conn:
            total_invested = sum([await conn.fetchval(f'SELECT SUM(investment) FROM users_shard_{i}') or 0 for i in range(10)])
            total_paid_out = await conn.fetchval('SELECT SUM(payout_received) FROM users_shard_0') or 0
        stability_index = total_invested / max(1, total_paid_out)
        stability_forecast = stability_index # Здесь можно использовать более сложный прогноз
        advice = ""
        if stability_forecast < 1.5:
            advice = "⚠️ Риск краха! Приглашай рефералов для стабильности."
        elif stability_forecast > 2:
            advice = "🟢 Децентрализованная сеть стабильна! Можно увеличить выплаты."
        else:
            advice = "🟡 Баланс норм, но пушь рефералов для роста."
        output = f"🌟 Ты звезда неоновой Пирамиды Богатства! 🤑\n"
        user = await get_user(user_id) # Removed w3, usd_token
        if random.random() < 0.1 and user:
            bonus = 10
            # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
            #     tx = usd_token.functions.mintForPayment(user['address'], int(bonus * 1e18)).buildTransaction({
            #         'from': w3.eth.default_account,
            #         'gas': 100000,
            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #     })
            #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            await update_user(user_id, {'gameBalances': user['gameBalances'] + bonus})
            output += f"🎁 Сюрприз, {user['name']}! +{bonus} USDToken за активность!\n"
        output += f"🏰 Децентрализованная сеть Пирамиды 🏰\n"
        payout_percent = await get_payout_percent() # Get from Redis
        output += f"Процент выплат: {payout_percent*100:.2f}% 📈\n"
        output += f"Стабильность: {stability_index:.2f}\nПрогноз: {stability_forecast:.2f} 🧠\n{advice}\n"
        if event_active and event_end:
            time_left = (event_end - datetime.now()).total_seconds()
            if time_left > 0:
                output += f"⏰ Эксклюзивный ивент! До конца: {time_left / 3600:.1f} часов 🔥\n"
        tree = await redis.get("referral_tree")
        if not tree:
            # await cache_referral_tree() # Вызов функции из database.py
            tree = await redis.get("referral_tree")
        output += tree.decode() if tree else "Дерево рефералов строится...\n"
        output += f"\n💰 Итог токенизированной экономики:\nВложения: {total_invested:.2f} USDToken\nВыплаты: {total_paid_out:.2f} USDToken\nТвоя прибыль: {(total_invested - total_paid_out):.2f} USDToken\n"
        await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(output)