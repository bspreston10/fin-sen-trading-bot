import requests
from settings_loader import (TELEGRAM_API_KEY, TELEGRAM_CHAT_ID)

TELEGRAM_TOKEN = TELEGRAM_API_KEY
CHAT_ID = TELEGRAM_CHAT_ID

def send_telegram_alert(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Telegram alert failed: {e}")