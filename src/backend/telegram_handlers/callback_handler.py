from telegram import Update
from telegram.ext import ContextTypes

# Import individual handlers
from src.backend.telegram_handlers.admin_handler import admin
from src.backend.telegram_handlers.buy_power_handler import buy_power
from src.backend.telegram_handlers.daily_handler import daily
from src.backend.telegram_handlers.dashboard_handler import dashboard
from src.backend.telegram_handlers.join_handler import join
from src.backend.telegram_handlers.leaderboard_handler import leaderboard
from src.backend.telegram_handlers.lottery_handler import lottery
from src.backend.telegram_handlers.status_handler import status
from src.backend.telegram_handlers.vote_handler import vote
from src.backend.telegram_handlers.withdraw_handler import withdraw

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "join":
        await query.message.reply_text("Введи: /join <имя> <сумма> [<реф_код>]")
    elif query.data == "buy_power":
        await query.message.reply_text("Введи: /buy_power <кол-во>")
    elif query.data == "status":
        await status(query, context)
    elif query.data == "leaderboard":
        await leaderboard(query, context)
    elif query.data == "daily":
        await daily(query, context)
    elif query.data == "lottery":
        await lottery(query, context)
    elif query.data == "withdraw":
        await withdraw(query, context)
    elif query.data == "admin":
        await admin(query, context)
    elif query.data == "dashboard":
        await dashboard(query, context)
    elif query.data == "vote":
        await query.message.reply_text("Введи: /vote <процент>")