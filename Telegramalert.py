# telegram_alert.py
import requests

BOT_TOKEN = "7701018588:AAEjcMhWCAmd-pgYtgSGgXaFUHpJoK8KO6k"
CHAT_ID = "5904387124"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # Optional: lets you use *bold* or _italic_
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"🚫 Telegram alert failed: {e}")