import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger
from src.backend.database import get_user, update_user, add_transaction, check_transaction_limit
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.game_logic import verify_captcha, verify_mfa, prove_balance
from src.backend.metrics import request_duration

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        if not await check_transaction_limit(user_id):
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                "Слишком много транзакций! Подожди час. ⏳"
            )
            return
        user = await get_user(user_id) # Removed w3, usd_token
        if not user:
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                "Ты не в игре! Вступи через /join 🤑"
            )
            return
        try:
            amount = float(context.args[0]) if context.args else user['gameBalances']
            if not await verify_captcha(user_id, "withdraw", amount):
                await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                    "Пройди проверку: https://captcha.pyramid.io"
                )
                return
            if not await verify_mfa(user_id):
                await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                    "Подтверди действие! Код MFA был отправлен тебе."
                )
                return
            if user['gameBalances'] < amount:
                await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                    "Недостаточно USDToken на балансе! 😢"
                )
                return
            proof = await prove_balance(user_id, amount)
            tx_hash = await add_transaction(user_id, -amount, 'withdraw')
            # if w3 and usd_token and PRIVATE_KEY: # Removed blockchain logic
            #     tx_burn = usd_token.functions.burnFromGame(user['address'], int(amount * 1e18)).buildTransaction({
            #         'from': w3.eth.default_account,
            #         'gas': 100000,
            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #     })
            #     signed_tx_burn = w3.eth.account.sign_transaction(tx_burn, private_key=PRIVATE_KEY)
            #     w3.eth.send_raw_transaction(signed_tx_burn.rawTransaction)
                
            #     tx_withdraw = contract.functions.withdraw().buildTransaction({
            #         'from': w3.eth.default_account,
            #         'gas': 100000,
            #         'nonce': w3.eth.get_transaction_count(w3.eth.default_account) + 1
            #     })
            #     signed_tx_withdraw = w3.eth.account.sign_transaction(tx_withdraw, private_key=PRIVATE_KEY)
            #     w3.eth.send_raw_transaction(signed_tx_withdraw.rawTransaction)
            await update_user(user_id, {'gameBalances': user['gameBalances'] - amount})
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                f"💸 Вывод {amount} USDToken успешен! Транзакция: {tx_hash}\nБаланс: {user['gameBalances'] - amount:.2f} USDToken"
            )
        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка в withdraw: {e}")
            await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(
                "Ошибка! Используй: /withdraw <сумма>"
            )