import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger
from src.backend.database import pool, get_user, update_user, update_lottery_pool, get_lottery_pool
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.metrics import request_duration

async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        user = await get_user(user_id) # Removed w3, usd_token
        if not user:
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)("Ты не в игре! Вступи через /join 🤑")
            return
        try:
            ticket_count = int(context.args[0]) if context.args else 1
            ticket_cost = 10
            total_cost = ticket_count * ticket_cost
            if user['gameBalances'] < total_cost:
                await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)("Недостаточно USDToken для покупки билетов! 😢")
                return
            # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
            #     tx = usd_token.functions.burnFromGame(user['address'], int(total_cost * 1e18)).buildTransaction({
            #         'from': w3.eth.default_account,
            #         'gas': 100000,
            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #     })
            #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            await update_user(user_id, {'gameBalances': user['gameBalances'] - total_cost})
            async with pool.acquire() as conn:
                await conn.execute('INSERT OR REPLACE INTO lottery_tickets (user_id, ticket_count) VALUES ($1, $2)',
                                  user_id, ticket_count)
            await update_lottery_pool(total_cost * 0.8) # Update in Redis
            lottery_pool_amount = await get_lottery_pool() # Get from Redis
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                f"🎰 Куплено {ticket_count} билетов за {total_cost} USDToken! Текущий призовой фонд: {lottery_pool_amount:.2f} USDToken"
            )
        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка в lottery: {e}")
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                "Ошибка! Используй: /lottery <кол-во_билетов>"
            )