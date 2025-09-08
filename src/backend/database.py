import asyncio
import json
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import aioredis
from asyncpg import create_pool

from src.backend.config import REDIS_URL, POSTGRES_DSN, QUESTS, ACHIEVEMENTS, logger, REDIS_KEY_PAYOUT_PERCENT, REDIS_KEY_LOTTERY_POOL

# Redis для кэширования
redis = aioredis.from_url(REDIS_URL)

# PostgreSQL пул
async def init_db_pool():
    return await create_pool(dsn=POSTGRES_DSN)

pool = None # Будет инициализирован в main

# SQLite резерв
@contextmanager
def get_db():
    conn = sqlite3.connect('pyramid.db')
    try:
        yield conn
    finally:
        conn.close()

def init_sqlite_db():
    with get_db() as conn:
        c = conn.cursor()
        for shard in range(10):
            c.execute(f'''
                CREATE TABLE IF NOT EXISTS users_shard_{shard} (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    investment REAL DEFAULT 0,
                    power REAL DEFAULT 0,
                    payout_received REAL DEFAULT 0,
                    gameBalances REAL DEFAULT 0,
                    last_update TIMESTAMP,
                    return_boost REAL DEFAULT 0,
                    referrals INTEGER DEFAULT 0,
                    parent_id INTEGER,
                    rank TEXT,
                    vip INTEGER DEFAULT 0,
                    fan_speed_bonus REAL DEFAULT 0,
                    achievements TEXT DEFAULT '',
                    guild_id INTEGER DEFAULT 0,
                    address TEXT,
                    mfa_token TEXT
                )
            ''')
            c.execute(f'CREATE INDEX IF NOT EXISTS idx_users_shard_{shard}_user_id ON users_shard_{shard}(user_id)')
            c.execute(f'CREATE INDEX IF NOT EXISTS idx_users_shard_{shard}_parent_id ON users_shard_{shard}(parent_id)')
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_hash TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                timestamp TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                user_id INTEGER,
                quest_id TEXT,
                progress INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, quest_id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                name TEXT,
                members INTEGER DEFAULT 0,
                bonus REAL DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                user_id INTEGER,
                ticket_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id)
            )
        ''')
        conn.commit()

async def get_user(user_id): # Removed w3_instance, usd_token_contract
    shard = user_id % 10
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    async with pool.acquire() as conn:
        user = await conn.fetchrow(f'SELECT * FROM users_shard_{shard} WHERE user_id = $1', user_id)
    if user:
        user = dict(user) # Преобразуем Record в dict для модификации
        # if w3_instance and usd_token_contract and user['address']: # Removed blockchain logic
        #     try:
        #         user['gameBalances'] = usd_token_contract.functions.balanceOf(user['address']).call() / 1e18
        #     except Exception as e:
        #         logger.error(f"Ошибка получения баланса USDToken для {user_id}: {e}")
        #         user['gameBalances'] = 0
        # else:
        #     user['gameBalances'] = 0
        # For now, gameBalances will be directly from DB or calculated
        user['gameBalances'] = user.get('gameBalances', 0) # Ensure it's present

        # Получаем квесты пользователя
        async with pool.acquire() as conn:
            user_quests_raw = await conn.fetch('SELECT quest_id, progress FROM quests WHERE user_id = $1', user_id)
            user_quests = []
            for q_raw in user_quests_raw:
                quest_info = QUESTS.get(q_raw['quest_id'], {})
                user_quests.append({
                    'id': q_raw['quest_id'],
                    'task': quest_info.get('task', 'Неизвестный квест'),
                    'progress': q_raw['progress'],
                    'total': 2 if q_raw['quest_id'] == 'invite_2' else 7 if q_raw['quest_id'] == 'weekly_active' else 1, # Пример логики для total
                    'reward': quest_info.get('reward', 0)
                })
            user['quests'] = user_quests

        # Получаем достижения пользователя
        user_achievements_str = user.get('achievements', '')
        user_achieved_list = user_achievements_str.split(',') if user_achievements_str else []
        user_achievements = []
        for ach_id, ach_info in ACHIEVEMENTS.items():
            user_achievements.append({
                'id': ach_id,
                'task': ach_info['task'],
                'completed': ach_id in user_achieved_list
            })
        user['achievements'] = user_achievements

        # Получаем данные для лидерборда (упрощенно для API)
        leaderboard_data = []
        for shard_idx in range(10):
            leaderboard_data.extend(await conn.fetch(f'SELECT name, investment, gameBalances FROM users_shard_{shard_idx} ORDER BY investment DESC LIMIT 10'))
        user['leaderboard'] = sorted(leaderboard_data, key=lambda x: x['investment'], reverse=True)[:10]


        await redis.set(f"user:{user_id}", json.dumps(dict(user)), ex=3600)
    return user

async def update_user(user_id, fields):
    shard = user_id % 10
    async with pool.acquire() as conn:
        set_clause = ', '.join([f"{k} = ${i+1}" for i, k in enumerate(fields.keys())])
        values = list(fields.values()) + [user_id]
        await conn.execute(f'UPDATE users_shard_{shard} SET {set_clause} WHERE user_id = ${len(values)}', *values)
    await redis.delete(f"user:{user_id}")

async def add_transaction(user_id, amount, tx_type):
    import hashlib
    import random
    from src.backend.metrics import transactions_total

    tx_hash = hashlib.sha256(str(random.random()).encode()).hexdigest()[:32]
    transactions_total.inc(labels={'type': tx_type})
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO transactions (tx_hash, user_id, amount, type, timestamp) VALUES ($1, $2, $3, $4, $5)',
                          tx_hash, user_id, amount, tx_type, datetime.now())
    return tx_hash

async def check_transaction_limit(user_id):
    key = f"tx_limit:{user_id}"
    count = await redis.get(key)
    if count and int(count) >= 5:
        return False
    await redis.incr(key)
    await redis.expire(key, 3600)
    return True

async def cache_referral_tree(get_user_func):
    async def build_tree(user_id, pre=''):
        user = await get_user_func(user_id)
        if not user:
            return ''
        # fan_speed = FAN_SPEED_BASE + user['power'] * 0.1 + user['fan_speed_bonus'] # Эти поля могут быть не в user
        # return_rate = BASE_RETURN + user['power'] * 0.1 + user['return_boost'] # Эти поля могут быть не в user
        line = f"{pre}{user['name']}: Внёс {user['investment']} USDToken, Мощность {user['power']} ⚡, Баланс {user['gameBalances']:.2f} USDToken, Рефералы {user['referrals']}\n"
        async with pool.acquire() as conn:
            children = await conn.fetch(f'SELECT user_id FROM users_shard_{user_id % 10} WHERE parent_id = $1', user_id)
        for child in children:
            line += await build_tree(child['user_id'], pre + '├── ')
        return line
    tree = await build_tree(0) # Предполагаем, что 0 - это корневой пользователь или начальная точка
    await redis.set("referral_tree", tree, ex=3600)

# New functions for Redis-managed global state
async def get_payout_percent():
    percent = await redis.get(REDIS_KEY_PAYOUT_PERCENT)
    return float(percent) if percent else 0.25 # Default value

async def set_payout_percent(percent):
    await redis.set(REDIS_KEY_PAYOUT_PERCENT, str(percent))

async def get_lottery_pool():
    pool_amount = await redis.get(REDIS_KEY_LOTTERY_POOL)
    return float(pool_amount) if pool_amount else 0.0 # Default value

async def update_lottery_pool(amount_delta):
    await redis.incrbyfloat(REDIS_KEY_LOTTERY_POOL, amount_delta)