import asyncio
import hashlib
import random
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import (
    logger, MAX_LEVELS, POWER_COST, BASE_RETURN, FAN_SPEED_BASE, QUESTS
)
from src.backend.database import (
    pool, get_user, update_user, add_transaction, check_transaction_limit, redis, get_payout_percent
)
# from src.backend.blockchain import ( # Removed
#     w3, contract, usd_token, contract_nft, execute_contract_join
# )
from src.backend.game_logic import (
    get_rank, check_vip, check_achievements, generate_dynamic_quest,
    optimize_referral_bonus_game_theory, verify_captcha
)
from src.backend.metrics import joins_total, request_duration

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        joins_total.inc()
        user_id = update.message.from_user.id
        if not await check_transaction_limit(user_id):
            await update.message.reply_text("Слишком много транзакций! Подожди час. ⏳")
            return
        try:
            args = context.args
            name, amount = args[0], float(args[1])
            if not await verify_captcha(user_id, "join", amount):
                await update.message.reply_text("Пройди проверку: https://captcha.pyramid.io")
                return
            referral_code = args[2] if len(args) > 2 else None
            parent_id = 0
            # user_address = w3.eth.account.create().address if w3 else f"0x{hashlib.sha256(str(user_id).encode()).hexdigest()[:40]}" # Removed blockchain logic
            user_address = f"0x{hashlib.sha256(str(user_id).encode()).hexdigest()[:40]}" # Mock address
            if referral_code:
                ref_user_id = int(referral_code.split('_')[1])
                parent_id = ref_user_id
                ref_user = await get_user(ref_user_id) # Removed w3, usd_token
                if ref_user:
                    bonus = optimize_referral_bonus_game_theory(ref_user['referrals'] + 1, ref_user['investment'])
                    # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
                    #     tx = usd_token.functions.mintForPayment(ref_user['address'], int(10 * (ref_user['referrals'] + 1) * 1e18)).buildTransaction({
                    #         'from': w3.eth.default_account,
                    #         'gas': 100000,
                    #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
                    #     })
                    #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                    #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    await update_user(ref_user_id, {
                        'referrals': ref_user['referrals'] + 1,
                        'gameBalances': ref_user['gameBalances'] + 10 * (ref_user['referrals'] + 1),
                        'return_boost': ref_user['return_boost'] + bonus
                    })
                    bonuses = [0.1, 0.05, 0.02, 0.01, 0.005]
                    current_id = ref_user_id
                    for level, bonus in enumerate(bonuses):
                        if level >= MAX_LEVELS:
                            break
                        current = await get_user(current_id) # Removed w3, usd_token
                        if current and current['parent_id']:
                            # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
                            #     tx = usd_token.functions.mintForPayment(current['address'], int(amount * bonus * 1e18)).buildTransaction({
                            #         'from': w3.eth.default_account,
                            #         'gas': 100000,
                            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
                            #     })
                            #     signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                            #     w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                            parent_user = await get_user(current['parent_id']) # Fetch parent user to update their balance
                            await update_user(current['parent_id'], {
                                'return_boost': parent_user['return_boost'] + bonus,
                                'gameBalances': parent_user['gameBalances'] + amount * bonus
                            })
                            current_id = current['parent_id']
                        else:
                            break
                    async with pool.acquire() as conn:
                        quest = await conn.fetchrow('SELECT progress FROM quests WHERE user_id = $1 AND quest_id = $2', ref_user_id, "invite_2")
                        if quest and quest['progress'] < 2:
                            await conn.execute('UPDATE quests SET progress = progress + 1 WHERE user_id = $1 AND quest_id = $2', ref_user_id, "invite_2")
                            if quest['progress'] + 1 >= 2:
                                await update_user(ref_user_id, {'return_boost': ref_user['return_boost'] + QUESTS['invite_2']['reward']})
                                await update.message.reply_text(f"Реферальный квест выполнен! 🎉 {ref_user['name']}, +{QUESTS['invite_2']['reward']} к доходности!")
                    if ref_user['referrals'] + 1 >= 3:
                        await update_user(ref_user_id, {'power': ref_user['power'] + 0.1})
                        await update.message.reply_text(f"Реферальный бонус! 🎉 {ref_user['name']}, +0.1 мощности!")
                    if ref_user['referrals'] + 1 >= 10:
                        await update_user(ref_user_id, {'name': f"🏅 Рекрутёр {ref_user['name']}", 'fan_speed_bonus': ref_user['fan_speed_bonus'] + 0.1})
                    if ref_user['referrals'] + 1 >= 50:
                        await update_user(ref_user_id, {'name': f"💎 Магнат {ref_user['name']}", 'fan_speed_bonus': ref_user['fan_speed_bonus'] + 0.2})
            # tx_hash = await execute_contract_join(user_id, amount, parent_id) # Removed blockchain logic
            tx_hash = hashlib.sha256(str(random.random()).encode()).hexdigest()[:32] # Mock tx_hash
            await add_transaction(user_id, amount, 'join') # Record transaction
            async with pool.acquire() as conn:
                shard = user_id % 10
                await conn.execute(
                    f'INSERT OR REPLACE INTO users_shard_{shard} (user_id, name, investment, gameBalances, last_update, parent_id, rank, address) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)',
                    user_id, name, amount, amount, datetime.now().isoformat(), parent_id, get_rank(amount), user_address
                )
            user = await get_user(user_id) # Removed w3, usd_token
            await check_vip(user_id)
            payout_percent = await get_payout_percent() # Get from Redis
            payout_per_level = amount * payout_percent
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
            async with pool.acquire() as conn:
                quest = await conn.fetchrow('SELECT progress FROM quests WHERE user_id = $1 AND quest_id = $2', user_id, "invest_500")
                if quest and amount >= 500:
                    await conn.execute('UPDATE quests SET progress = 1 WHERE user_id = $1 AND quest_id = $2', user_id, "invest_500")
                    await update_user(user_id, {'power': user['power'] + QUESTS['invest_500']['reward']})
                    await update.message.reply_text(f"Квест выполнен! 🎉 {name}, +{QUESTS['invest_500']['reward']} мощность за вложение 500 USDToken!")
            await generate_dynamic_quest(user_id, pool)
            await check_achievements(user_id)
            fan_speed = FAN_SPEED_BASE + user['power'] * 0.1 + user['fan_speed_bonus']
            await update.message.reply_text(
                f"{name}, добро пожаловать в неоновую эру богатства! 🎉\n"
                f"Внёс: {amount} USDToken\nРанг: {get_rank(amount)}\n"
                f"Твой реф-код: ref_{user_id}\nВентилятор пассивного дохода: {fan_speed:.2f}x ⚡\n"
                f"Баланс: {user['gameBalances']:.2f} USDToken\n"
                f"Смарт-контракт: {tx_hash} 🛡️\nПроверить: https://blockchain.pyramid.io/tx/{tx_hash}"
            )
        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка в join: {e}")
            await update.message.reply_text("Ошибка! Используй: /join <имя> <сумма> [<реф_код>]")