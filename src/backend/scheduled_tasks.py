import asyncio
import pandas as pd
import numpy as np
import torch
import random
import boto3
from datetime import datetime, timedelta

from src.backend.config import (
    logger, BASE_RETURN, FAN_SPEED_BASE,
    ACHIEVEMENTS, QUESTS, YOUR_ADMIN_ID
)
from src.backend.database import pool, get_user, update_user, get_db, redis, get_payout_percent, set_payout_percent
from src.backend.metrics import stability_gauge, events_active
from src.backend.ml_models import AdvancedStabilityPredictor, EventOptimizer, create_anomaly_detector
# from src.backend.blockchain import w3, contract, usd_token, contract_nft, PRIVATE_KEY # Removed

# Глобальные переменные для состояния (будут управляться в main или через Redis)
stability_data = []
event_active = False
event_end = None
event_optimizer = EventOptimizer()
stability_predictor = AdvancedStabilityPredictor()
stability_optimizer = torch.optim.Adam(stability_predictor.parameters(), lr=0.0005)
stability_criterion = torch.nn.MSELoss()


async def update_fan_profits_task():
    async with pool.acquire() as conn:
        for shard in range(10):
            users = await conn.fetch(f'SELECT user_id, power, gameBalances, last_update, return_boost, fan_speed_bonus FROM users_shard_{shard}')
            updates = []
            for user in users:
                time_diff = (datetime.now() - datetime.fromisoformat(user['last_update'])).total_seconds()
                fan_speed = FAN_SPEED_BASE + user['power'] * 0.1 + user['fan_speed_bonus']
                boost = 1.5 if event_active else 1
                new_balance = user['gameBalances'] + time_diff * fan_speed * (BASE_RETURN + user['return_boost']) * boost
                updates.append((new_balance, datetime.now().isoformat(), user['user_id']))
            await conn.executemany(f'UPDATE users_shard_{shard} SET gameBalances = $1, last_update = $2 WHERE user_id = $3', updates)

async def optimize_payout_dynamic():
    current_payout_percent = await get_payout_percent()
    while True:
        async with pool.acquire() as conn:
            new_participants = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i} WHERE (julianday("now") - julianday(last_update)) <= 7') for i in range(10)])
            total_users = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i}') or 1 for i in range(10)])
            total_invested = sum([await conn.fetchval(f'SELECT SUM(investment) FROM users_shard_{i}') or 0 for i in range(10)])
            total_paid_out = await conn.fetchval('SELECT SUM(amount) FROM transactions WHERE type = "withdraw"') or 0
            churn_rate = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i} WHERE (julianday("now") - julianday(last_update)) > 30') for i in range(10)]) / total_users
        
        growth_rate = new_participants / total_users
        avg_invest = total_invested / total_users
        
        # Placeholder for calculate_stability_derivative, assuming it's defined elsewhere or simplified
        # from src.backend.game_logic import calculate_stability_derivative
        # stability = calculate_stability_derivative(growth_rate, avg_invest, current_payout_percent, total_paid_out, churn_rate)
        
        # Simplified stability calculation for now
        stability = (growth_rate * avg_invest) - (current_payout_percent * total_paid_out) - (churn_rate * 100) # Example simplified formula

        if stability < 0:
            current_payout_percent = max(0.1, current_payout_percent - 0.05)
        elif stability > 1000:
            current_payout_percent = min(0.5, current_payout_percent + 0.05)
        await set_payout_percent(current_payout_percent)
        logger.info(f"Динамический payout_percent: {current_payout_percent}")
        # await notify_all_users(f"📢 Обновление процента выплат: {current_payout_percent*100}%")
        await asyncio.sleep(24 * 3600)

async def advanced_analyze(app_instance): # app_instance для доступа к боту
    global stability_data, event_active, event_end, stability_predictor, stability_optimizer, stability_criterion
    current_payout_percent = await get_payout_percent()
    while True:
        async with pool.acquire() as conn:
            new_participants = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i} WHERE (julianday("now") - julianday(last_update)) <= 7') for i in range(10)])
            total_users = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i}') or 1 for i in range(10)])
            total_invested = sum([await conn.fetchval(f'SELECT SUM(investment) FROM users_shard_{i}') or 0 for i in range(10)])
            total_paid_out = await conn.fetchval('SELECT SUM(amount) FROM transactions WHERE type = "withdraw"') or 0
            avg_tx_time = await conn.fetchval('SELECT AVG(julianday("now") - julianday(timestamp)) FROM transactions') or 0
            total_referrals = sum([await conn.fetchval(f'SELECT SUM(referrals) FROM users_shard_{i}') or 0 for i in range(10)])
            active_users = sum([await conn.fetchval(f'SELECT COUNT(*) FROM users_shard_{i} WHERE (julianday("now") - julianday(last_update)) <= 30') for i in range(10)])
        
        data = pd.DataFrame({
            'growth': [new_participants / total_users],
            'avg_invest': [total_invested / total_users],
            'withdrawals': [total_paid_out],
            'avg_tx_time': [avg_tx_time],
            'referral_rate': [total_referrals / total_users],
            'retention_rate': [active_users / total_users]
        })
        stability_data.append(data)
        if len(stability_data) > 20:
            stability_data.pop(0)
        
        if len(stability_data) >= 10:
            inputs = torch.tensor(pd.concat(stability_data[-10:]).values, dtype=torch.float32).unsqueeze(0)
            targets = torch.tensor([total_invested / max(1, total_paid_out)] * inputs.shape[1], dtype=torch.float32)
            for _ in range(30):
                stability_optimizer.zero_grad()
                outputs = stability_predictor(inputs).squeeze()
                loss = stability_criterion(outputs, targets)
                loss.backward()
                stability_optimizer.step()
        
        input_tensor = torch.tensor(data.values, dtype=torch.float32).unsqueeze(0)
        stability_forecast = stability_predictor(input_tensor).item()
        stability_gauge.set(stability_forecast)
        
        if stability_forecast < 1.0:
            await set_payout_percent(0.3)
            if app_instance: # Проверяем, что app_instance передан
                await app_instance.bot.send_message(YOUR_ADMIN_ID, "🚨 Критический риск краха! Запускаю экстренный ивент!")
            asyncio.create_task(start_emergency_event(app_instance))
        logger.info(f"Прогноз стабильности: {stability_forecast:.2f}")
        await asyncio.sleep(24 * 3600)

async def detect_anomalies():
    anomaly_detector = create_anomaly_detector()
    async with pool.acquire() as conn:
        data = []
        for shard in range(10):
            data.extend(await conn.fetch(f'SELECT user_id, investment, gameBalances, referrals FROM users_shard_{shard}'))
    X = [[row['investment'], row['gameBalances'], row['referrals']] for row in data]
    if X:
        model = anomaly_detector
        anomalies = model.fit_predict(X)
        for i, row in enumerate(data):
            if anomalies[i] == -1:
                logger.warning(f"Обнаружена аномалия для пользователя {row['user_id']}")
                # await app.bot.send_message(YOUR_ADMIN_ID, f"⚠️ Аномалия: пользователь {row['user_id']} с инвестицией {row['investment']}")

async def circuit_breaker():
    while True:
        async with pool.acquire() as conn:
            total_invested = sum([await conn.fetchval(f'SELECT SUM(investment) FROM users_shard_{i}') or 0 for i in range(10)])
            total_paid_out = await conn.fetchval('SELECT SUM(amount) FROM transactions WHERE type = "withdraw"') or 0
        stability_forecast = total_invested / max(1, total_paid_out)
        if stability_forecast < 0.5:
            global event_active
            event_active = False
            # await notify_all_users("🚨 Система приостановлена: критическая нестабильность!")
        await asyncio.sleep(3600)

async def start_emergency_event(app_instance):
    global event_active, event_end
    event_active = True
    events_active.inc()
    event_end = datetime.now() + timedelta(hours=48)
    if app_instance:
        # await notify_all_users("🚨 ЭКСТРЕННЫЙ ИВЕНТ! Вложи 100+ USDToken за 48ч и получи +0.5 мощности! 🔥")
        pass # Заглушка, так как notify_all_users не определена здесь

async def auto_events(app_instance):
    global event_active, event_end
    while True:
        if (datetime.now().hour % 24 == 0) and not event_active:
            event = await event_optimizer.propose_event(pool)
            event_active = True
            events_active.inc()
            event_end = datetime.now() + timedelta(hours=event['duration'])
            if app_instance:
                # await notify_all_users(f"⏰ ЭКСКЛЮЗИВНЫЙ ИВЕНТ! Вложи 200+ USDToken за {event['duration']}ч и получи +{event['reward']} мощности! 🔥")
                pass # Заглушка
        if event_active and datetime.now() > event_end:
            event_active = False
            events_active.dec()
            async with pool.acquire() as conn:
                users = []
                for shard in range(10):
                    users.extend(await conn.fetch(f'SELECT user_id, investment FROM users_shard_{shard} WHERE investment >= 200 AND (julianday("now") - julianday(last_update)) <= 1'))
            for user in users:
                await update_user(user['user_id'], {'power': (await get_user(user['user_id']))['power'] + event['reward']}) # Removed w3, usd_token
                if app_instance:
                    # await app_instance.bot.send_message(user['user_id'], f"🎉 Ивент окончен! +{event['reward']} мощности за вложения 200+ USDToken!")
                    pass # Заглушка
        await asyncio.sleep(6 * 3600)

async def retention_bonus(app_instance):
    while True:
        async with pool.acquire() as conn:
            inactive_users = []
            for shard in range(10):
                inactive_users.extend(await conn.fetch(f'SELECT user_id FROM users_shard_{shard} WHERE (julianday("now") - julianday(last_update)) > 14'))
        for user in inactive_users:
            bonus = random.uniform(0.1, 0.3)
            await update_user(user['user_id'], {'return_boost': (await get_user(user['user_id']))['return_boost'] + bonus}) # Removed w3, usd_token
            if app_instance:
                # await app_instance.bot.send_message(user['user_id'], f"Вернись в игру! 🎁 Бонус: +{bonus:.2f} к доходности!")
                pass # Заглушка
        await asyncio.sleep(24 * 3600)

async def backup_db():
    s3 = boto3.client('s3')
    with get_db() as conn:
        with open('pyramid_backup.db', 'wb') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n'.encode())
    # Замени 'my-bucket' на имя твоего S3 бакета
    s3.upload_file('pyramid_backup.db', 'my-bucket', f'backup_{datetime.now().isoformat()}.db')