from aiohttp import web
from datetime import datetime

from src.backend.database import get_user, check_transaction_limit
from src.backend.payment_handlers import create_payment_api # Import the new handler

async def get_user_data_api(request):
    user_id = int(request.match_info['user_id'])
    user_data = await get_user(user_id) # Removed w3, usd_token parameters
    if user_data:
        user_dict = dict(user_data)
        user_dict.pop('mfa_token', None)
        user_dict.pop('address', None) 
        
        if 'last_update' in user_dict and isinstance(user_dict['last_update'], datetime):
            user_dict['last_update'] = user_dict['last_update'].isoformat()

        for key, value in user_dict.items():
            if isinstance(value, (float, int)):
                user_dict[key] = float(value)
            elif isinstance(value, bytes):
                user_dict[key] = value.decode('utf-8')

        return web.json_response(user_dict)
    return web.json_response({"error": "User not found"}, status=404)

async def check_transaction_limit_api(request):
    user_id = int(request.match_info['user_id'])
    allowed = await check_transaction_limit(user_id)
    return web.json_response({"allowed": allowed})