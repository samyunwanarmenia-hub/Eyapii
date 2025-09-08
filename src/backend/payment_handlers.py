from aiohttp import web
import aiohttp
from src.backend.config import NOWPAYMENTS_API_KEY, logger

async def create_payment_api(request):
    if not NOWPAYMENTS_API_KEY:
        logger.error("NOWPAYMENTS_API_KEY is not set in environment variables.")
        return web.json_response({"error": "Payment service not configured"}, status=500)

    try:
        data = await request.json()
        user_id = data.get('user_id')
        usd_amount = data.get('amount')

        if not user_id or not usd_amount or usd_amount <= 0:
            return web.json_response({"error": "Invalid user_id or amount"}, status=400)

        async with aiohttp.ClientSession() as session:
            nowpayments_response = await session.post('https://api.nowpayments.io/v1/payment',
                headers={
                    'x-api-key': NOWPAYMENTS_API_KEY,
                    'Content-Type': 'application/json'
                },
                json={
                    'price_amount': usd_amount,
                    'price_currency': 'usd',
                    'pay_currency': 'dash', # Or any other preferred crypto currency
                    'ipn_callback_url': 'https://eyapi.netlify.app/api/nowpayments_callback', # Updated to your Netlify URL with a backend endpoint
                    'order_id': str(user_id) # Ensure order_id is a string
                }
            )
            nowpayments_data = await nowpayments_response.json()

            if nowpayments_response.ok:
                logger.info(f"NowPayments payment created for user {user_id}: {nowpayments_data}")
                return web.json_response({"success": True, "payment_data": nowpayments_data})
            else:
                logger.error(f"NowPayments API error for user {user_id}: {nowpayments_data}")
                return web.json_response({"success": False, "error": nowpayments_data.get('message', 'NowPayments API error')}, status=nowpayments_response.status)

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)