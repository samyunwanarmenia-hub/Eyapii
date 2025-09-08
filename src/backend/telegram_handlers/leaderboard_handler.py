import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from src.backend.config import logger
from src.backend.database import pool
from src.backend.metrics import request_duration

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with request_duration.time():
        async with pool.acquire() as conn:
            users = []
            for shard in range(10):
                users.extend(await conn.fetch(f'SELECT name, investment, referrals FROM users_shard_{shard} ORDER BY investment DESC LIMIT 10'))
            users = sorted(users, key=lambda x: x['investment'], reverse=True)[:10]
        output = "🏆 Топ-10 Богатеев 🏆\n"
        for i, user in enumerate(users, 1):
            tier = "🥉 Bronze" if user['investment'] < 1000 else "🥈 Silver" if user['investment'] < 5000 else "🥇 Gold"
            output += f"{i}. {user['name']} ({tier}): {user['investment']:.2f} USDToken, Рефералы: {user['referrals']}\n"
        await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)(output)