import hashlib
import random
from datetime import datetime, timedelta

# from py_ecc.bn128 import G1, multiply # Removed

from src.backend.config import (
    POWER_COST, BASE_RETURN, FAN_SPEED_BASE, MAX_LEVELS,
    QUESTS, ACHIEVEMENTS, logger
)
from src.backend.database import get_user, update_user, add_transaction, redis, get_payout_percent
# from src.backend.blockchain import w3, contract, usd_token, contract_nft, PRIVATE_KEY # Removed

def get_rank(investment):
    if investment < 500:
        return "Новичок 🐣"
    elif investment <= 1000:
        return "Босс 😎"
    elif investment <= 5000:
        return "Император 👑"
    return "Легенда 🔥"

async def check_vip(user_id):
    user = await get_user(user_id) # Removed w3, usd_token
    if user and user['investment'] >= 5000 and user['vip'] == 0:
        await update_user(user_id, {'vip': 1, 'name': f"🌟 {user['name']} [VIP]"})
    return user

async def check_achievements(user_id):
    user = await get_user(user_id) # Removed w3, usd_token
    if user:
        gameBalances = user['gameBalances']
        referrals = user['referrals']
        power = user['power']
        achievements_str = user['achievements']
        achieved = achievements_str.split(',') if achievements_str else []

        # Достижение "Первый миллион"
        if gameBalances >= 1_000_000 and "first_million" not in achieved:
            await update_user(user_id, {'power': user['power'] + ACHIEVEMENTS['first_million']['reward'], 'achievements': achievements_str + ',first_million'})
            # await app.bot.send_message(user_id, "🏆 Достижение: Первый миллион! +0.5 мощности!")
            # if w3 and contract_nft and user['address'] and PRIVATE_KEY: # Removed blockchain logic
            #     try:
            #         tx = contract_nft.functions.mint(user['address']).buildTransaction({
            #             'from': w3.eth.default_account,
            #             'gas': 100000,
            #             'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #         })
            #         signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            #         w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            #     except Exception as e:
            #         logger.error(f"Ошибка минта NFT для {user_id}: {e}")

        # Достижение "Реферальный титан"
        if referrals >= 100 and "referral_titan" not in achieved:
            # if w3 and usd_token and user['address'] and PRIVATE_KEY: # Removed blockchain logic
            #     try:
            #         tx = usd_token.functions.mintForPayment(user['address'], int(ACHIEVEMENTS['referral_titan']['reward'] * 1e18)).buildTransaction({
            #             'from': w3.eth.default_account,
            #             'gas': 100000,
            #             'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #         })
            #         signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            #         w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            #     except Exception as e:
            #         logger.error(f"Ошибка минта USDToken для реферального титана {user_id}: {e}")
            await update_user(user_id, {'gameBalances': user['gameBalances'] + ACHIEVEMENTS['referral_titan']['reward'], 'achievements': achievements_str + ',referral_titan'})
            # await app.bot.send_message(user_id, "🏆 Достижение: Реферальный титан! +1000 USDToken!")

        # Достижение "Мастер мощности"
        if power >= 10 and "power_master" not in achieved:
            # if w3 and usd_token and user['address'] and PRIVATE_KEY: # Removed blockchain logic
            #     try:
            #         tx = usd_token.functions.mintForPayment(user['address'], int(ACHIEVEMENTS['power_master']['reward'] * 1e18)).buildTransaction({
            #             'from': w3.eth.default_account,
            #             'gas': 100000,
            #             'nonce': w3.eth.get_transaction_count(w3.eth.default_account)
            #         })
            #         signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            #         w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            #     except Exception as e:
            #         logger.error(f"Ошибка минта USDToken для мастера мощности {user_id}: {e}")
            await update_user(user_id, {'gameBalances': user['gameBalances'] + ACHIEVEMENTS['power_master']['reward'], 'achievements': achievements_str + ',power_master'})
            # await app.bot.send_message(user_id, "🏆 Достижение: Мастер мощности! +500 USDToken!")

async def generate_dynamic_quest(user_id, pool):
    user = await get_user(user_id) # Removed w3, usd_token
    if user:
        if user['referrals'] < 5: # Изменено с 10 на 5 для более раннего квеста
            quest_id = f"dynamic_invite_{user_id}"
            task = f"Пригласи {5 - user['referrals']} друзей"
            reward = 0.2
            async with pool.acquire() as conn:
                await conn.execute('INSERT OR REPLACE INTO quests (user_id, quest_id, progress) VALUES ($1, $2, 0)', user_id, quest_id)
            # await app.bot.send_message(user_id, f"🎯 Новый квест: {task}! Награда: +{reward} мощности")
        if user['investment'] < 1000:
            quest_id = f"dynamic_invest_{user_id}"
            task = f"Вложи ещё {1000 - user['investment']} USDToken"
            reward = 0.3
            async with pool.acquire() as conn:
                await conn.execute('INSERT OR REPLACE INTO quests (user_id, quest_id, progress) VALUES ($1, $2, 0)', user_id, quest_id)
            # await app.bot.send_message(user_id, f"🎯 Новый квест: {task}! Награда: +{reward} к доходности")

def optimize_referral_bonus_game_theory(referrals, user_investment):
    base_bonus = 0.15
    cost_per_referral = 3
    max_bonus = 0.6
    bonus = base_bonus * min(referrals, 15) - cost_per_referral * referrals / max(1, user_investment)
    return min(max_bonus, max(0.05, bonus))

def calculate_stability_derivative(growth_rate, avg_invest, payout_percent, withdrawals, churn_rate):
    alpha, beta, gamma = 1.3, 1.0, 0.4
    return alpha * growth_rate * avg_invest - beta * payout_percent * withdrawals - gamma * churn_rate

async def verify_captcha(user_id, action, amount):
    if amount > 1000:
        # В реальном приложении здесь будет вызов к Telegram Bot API для отправки капчи
        # await app.bot.send_message(user_id, "Пройди проверку: https://captcha.pyramid.io")
        logger.info(f"Captcha required for user {user_id} for amount {amount}")
        return False
    return True

async def verify_mfa(user_id):
    user = await get_user(user_id) # Removed w3, usd_token
    if user and user['mfa_token']:
        token = hashlib.sha256(str(random.random()).encode()).hexdigest()[:8]
        await update_user(user_id, {'mfa_token': token})
        # await app.bot.send_message(user_id, f"Подтверди действие! Код MFA: {token}")
        logger.info(f"MFA required for user {user_id}, token: {token}")
        return False
    return True

async def prove_balance(user_id, amount):
    # user = await get_user(user_id, w3, usd_token) # Removed
    # secret = user['gameBalances'] # Removed
    # commitment = multiply(G1, int(secret * 1e18)) # Removed
    # proof = {"commitment": str(commitment), "amount": amount} # Removed
    # await redis.set(f"zkp:{user_id}", json.dumps(proof), ex=3600) # Removed
    # return proof # Removed
    logger.info(f"Mock ZKP for user {user_id} for amount {amount}")
    return {"mock_proof": "mock_data"} # Mock proof