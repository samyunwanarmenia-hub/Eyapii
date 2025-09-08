import asyncio
import random
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from src.backend.config import (
    logger, MAX_LEVELS, POWER_COST, BASE_RETURN, FAN_SPEED_BASE, QUESTS
)
from src.backend.database import (
    pool, get_user, update_user, add_transaction, check_transaction_limit, get_payout_percent
)
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.game_logic import (
    check_achievements, generate_dynamic_quest, verify_captcha, prove_balance
)
from src.backend.metrics import request_duration

async def buy_power(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.message.from_user.id
        if not await check_transaction_limit(user_id):
            await update.message.reply_text("Слишком много транзакций! Подожди час. ⏳")
            return
        try:
            power_amount = int(context.args[0])
            user = await get_user(user_id) # Removed w3, usd_token
            if user:
                cost = power_amount * POWER_COST
                if not await verify_captcha(user_id, "buy_power", cost):
                    await update.message.reply_text("Пройди проверку: https://captcha.pyramid.io")
                    return
                if user['gameBalances'] >= cost:
                    proof = await prove_balance(user_id, cost)
                    tx_hash = await add_transaction(user_id, -cost, 'buy_power')
                    # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
                    #     tx = usd_token.functions.burnFromGame(user['address'], int(cost * 1e18)).buildTransaction({
                    #         'from': w3.eth.default_account,
                    #         'gas': 100000,
                    #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
                    #     })
                    #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                    #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    await update_user(user_id, {'gameBalances': user['gameBalances'] - cost, 'power': user['power'] + power_amount})
                    payout_percent = await get_payout_percent() # Get from Redis
                    payout_per_level = cost * payout_percent
                    current_id = user_id
                    for level in range(MAX_LEVELS):
                        current = await get_user(current_id) # Removed w3, usd_token
                        if not current or not current['parent_id']:
                            break
                        # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
                        #     tx = usd_token.functions.mintForPayment(current['address'], int(payout_per_level * 1e18)).buildTransaction({
                        #         'from': w3.eth.default_account,
                        #         'gas': 100000,
                        #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
                        #     })
                        #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                        #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        parent_user = await get_user(current['parent_id']) # Fetch parent user to update their balance
                        await update_user(current['parent_id'], {
                            'payout_received': parent_user['payout_received'] + payout_per_level,
                            'gameBalances': parent_user['gameBalances'] + payout_per_level
                        })
                        current_id = current['parent_id']
                    fan_speed = FAN_SPEED_BASE + (user['power'] + power_amount) * 0.1 + user['fan_speed_bonus']
                    await update.message.reply_text(
                        f"{user['name']}, ты усилил вентилятор пассивного дохода! ⚡\n"
                        f"Куплено: {power_amount} мощности за {cost} USDToken\n"
                        f"Скорость: {fan_speed:.2f}x\n"
                        f"Доходность: {(BASE_RETURN + (user['power'] + power_amount) * 0.1 + user['return_boost'])*100:.2f}%/неделя\n"
                        f"Баланс: {user['gameBalances'] - cost:.2f} USDToken\n"
                        f"Смарт-контракт: {tx_hash} 🛡️\nПроверить: https://blockchain.pyramid.io/tx/{tx_hash}"
                    )
                    await check_achievements(user_id)
                    async with pool.acquire() as conn:
                        quest = await conn.fetchrow('SELECT progress FROM quests WHERE user_id = $1 AND quest_id = $2', user_id, "level_up")
                        if quest and user['power'] + power_amount >= 5:
                            # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
                            #     tx = usd_token.functions.mintForPayment(user['address'], int(QUESTS['level_up']['reward'] * 1e18)).buildTransaction({
                            #         'from': w3.eth.default_account,
                            #         'gas': 100000,
                            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
                            #     })
                            #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                            #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                            await conn.execute('UPDATE quests SET progress = 1 WHERE user_id = $1 AND quest_id = $2', user_id, "level_up")
                            await update_user(user_id, {'gameBalances': user['gameBalances'] + QUESTS['level_up']['reward']})
                            await update.message.reply_text(f"Квест выполнен! 🎉 {user['name']}, +{QUESTS['level_up']['reward']} USDToken за повышение уровня!")
                    await generate_dynamic_quest(user_id, pool)
                    return
                else:
                    await update.message.reply_text("Недостаточно USDToken! 😢 Вложи больше через /join или используй Telegram Stars.")
            await update.message.reply_text("Ты не в игре! Вступи через /join 🤑")
        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка в buy_power: {e}")
            await update.message.reply_text("Ошибка! Используй: /buy_power <кол-во>")