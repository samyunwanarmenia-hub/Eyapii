import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger
from src.backend.database import get_user, get_payout_percent, set_payout_percent # Added set_payout_percent
# from src.backend.blockchain import w3, contract, usd_token # Removed
from src.backend.metrics import request_duration

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        user_id = update.message.from_user.id
        user = await get_user(user_id) # Removed w3, usd_token
        if not user or user['investment'] < 1000:
            await update.message.reply_text("Нужно вложить 1000+ USDToken для голосования! 😎")
            return
        try:
            new_percent = float(context.args[0])
            # if not w3 or not contract or not PRIVATE_KEY: # Removed blockchain logic
            #     await update.message.reply_text("Блокчейн не подключен или приватный ключ отсутствует! 😢")
            #     return
            # tx = contract.functions.votePayout(int(new_percent * 100)).buildTransaction({ # Replaced with direct Redis update
            #     'from': w3.eth.default_account,
            #     'gas': 100000,
            #     'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            # })
            # signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            # tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            await set_payout_percent(new_percent / 100) # Update payout percent in Redis directly
            tx_hash = "mock_tx_hash_for_vote" # Mock transaction hash
            await update.message.reply_text(f"Голос за {new_percent}% отправлен! 🗳️ Транзакция: {tx_hash}")
        except (IndexError, ValueError) as e:
            logger.error(f"Ошибка в vote: {e}")
            await update.message.reply_text("Ошибка! Используй: /vote <процент>")