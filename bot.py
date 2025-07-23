import requests,time
from telebot import TeleBot
server_instance = None  # This will be set externally

# Telegram bot credentials
BOT_TOKEN = "7701018588:AAEjcMhWCAmd-pgYtgSGgXaFUHpJoK8KO6k"
CHAT_ID = "5904387124"

# Runtime state
alerts_active = True

sr_config = {
    "tolerance": 2.0,  # Default tolerance for support/resistance
    "support": [],
    "resistance": []
}

# Initialize bot instance
bot = TeleBot(BOT_TOKEN)


def send_telegram_alert(message):
    """
    Send a message to Telegram using Markdown formatting.
    This is also used for system messages and command feedback.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = send_with_retries(url, payload)
        response.raise_for_status()
    except Exception as e:
        print(f"🚫 Telegram alert failed: {e}")
@bot.message_handler(commands=["reset_server"])
def handle_reset(msg):
    if server_instance:
        server_instance.reset_state()
        send_telegram_alert("🔄 *Server state has been reset via Telegram.*")
    else:
        send_telegram_alert("⚠️ Cannot reset. Server not linked.")

# 🧭 Command: /pause
@bot.message_handler(commands=["pause"])
def handle_pause(msg):
    global alerts_active
    alerts_active = False
    send_telegram_alert("🔕 *Alert system paused.*")

# 🧭 Command: /resume
@bot.message_handler(commands=["resume"])
def handle_resume(msg):
    global alerts_active
    alerts_active = True
    send_telegram_alert("🔔 *Alert system resumed.*")

# 🛠️ Command: /set_sr 0.25
@bot.message_handler(commands=["set_sr"])
def handle_set_sr(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["tolerance"] = value
        send_telegram_alert(f"⚙️ *SR tolerance* updated to `{value}`")
    except:
        send_telegram_alert("⚠️ Usage: `/set_sr 0.25`")

# 📌 Command: /set_support 1920.5
@bot.message_handler(commands=["set_support"])
def handle_add_support(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["support"].append(value)
        send_telegram_alert(f"📌 *Support level* added: `{value}`")
    except:
        send_telegram_alert("⚠️ Usage: `/set_support 1920.5`")

# 📌 Command: /set_resistance 1975.0
@bot.message_handler(commands=["set_resistance"])
def handle_add_resistance(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["resistance"].append(value)
        send_telegram_alert(f"📍 *Resistance level* added: `{value}`")
    except:
        send_telegram_alert("⚠️ Usage: `/set_resistance 1975.0`")

# 📊 Command: /status
@bot.message_handler(commands=["status"])
def handle_status(msg):
    status = "🟢 active" if alerts_active else "🔴 paused"
    sr_levels = (
        f"- Tolerance: `{sr_config['tolerance']}`\n"
        f"- Support: `{', '.join(map(str, sr_config['support'])) or 'None'}`\n"
        f"- Resistance: `{', '.join(map(str, sr_config['resistance'])) or 'None'}`"
    )
    send_telegram_alert(f"📊 *System Status*\n- Alerts: {status}\n{sr_levels}")
def start_bot():
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"💥 Bot polling failed: {e}")
"""
    Starts the bot’s polling loop.
    Call this from your main script to begin listening for commands.
    """
def send_with_retries(url, payload, max_attempts=3, delay=5):
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            return response  # ✅ Success
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                print(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print("❌ All retry attempts failed.")