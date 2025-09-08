from .start_handler import start
from .callback_handler import button
from .join_handler import join
from .vote_handler import vote
from .buy_power_handler import buy_power
from .daily_handler import daily
from .lottery_handler import lottery
from .withdraw_handler import withdraw
from .admin_handler import admin
from .dashboard_handler import dashboard
from .status_handler import status
from .leaderboard_handler import leaderboard

# This function is not used directly for sending messages,
# as Telegram Bot API is called directly in handlers.
# If mass notification is needed, it should be implemented via Telegram Bot API.
async def notify_all_users(message):
    # logger.info(f"Mass notification: {message}")
    pass