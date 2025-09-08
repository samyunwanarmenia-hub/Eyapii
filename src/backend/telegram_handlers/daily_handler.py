import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger, QUESTS
from src.backend.database import pool, get_user, update_user, redis
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.metrics import request_duration

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        user = await get_user(user_id) # Removed w3, usd_token
        if not user:
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)("Ты не в игре! Вступи через /join 🤑")
            return
        key = f"daily:{user_id}"
        if await redis.get(key):
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)("Ежедневный бонус уже получен! Попробуй завтра. ⏳")
            return
        bonus = random.uniform(5, 20)
        # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
        #     tx = usd_token.functions.mintForPayment(user['address'], int(bonus * 1e18)).buildTransaction({
        #         'from': w3.eth.default_account,
        #         'gas': 100000,
        #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
        #     })
        #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        await update_user(user_id, {'gameBalances': user['gameBalances'] + bonus})
        await redis.set(key, "1", ex=24*3600)
        await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
            f"🎁 Ежедневный бонус! +{bonus:.2f} USDToken на твой баланс!"
        )
        async with pool.acquire() as conn:
            quest = await conn.fetchrow('SELECT progress FROM quests WHERE user_id = $1 AND quest_id = $2', user_id, "weekly_active")
            if quest:
                await conn.execute('UPDATE quests SET progress = progress + 1 WHERE user_id = $1 AND quest_id = $2', user_id, "weekly_active")
                if quest['progress'] + 1 >= 7:
                    await update_user(user_id, {'fan_speed_bonus': user['fan_speed_bonus'] + QUESTS['weekly_active']['reward']})
                    await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                        f"Квест выполнен! 🎉 {user['name']}, +{QUESTS['weekly_active']['reward']} к скорости вентилятора!"
                    )