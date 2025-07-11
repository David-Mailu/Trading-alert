# test_telegram.py
from Telegramalert import send_telegram_alert

test_message = "✅ Test Alert: Telegram bot is working!"
send_telegram_alert(test_message)
print("📤 Test message sent.")