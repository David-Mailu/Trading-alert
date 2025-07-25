import requests,time
from telebot import TeleBot
server_instance = None  # Global variable to hold the server instance

 # This will be set externally

# Telegram bot credentials
BOT_TOKEN = "7701018588:AAEjcMhWCAmd-pgYtgSGgXaFUHpJoK8KO6k"
CHAT_ID = "5904387124"


sr_config = {
    "tolerance": 2.0,  # Default tolerance for support/resistance
    "support": [],
    "resistance": []
}

# Initialize bot instance
bot = TeleBot(BOT_TOKEN)
 # Link the server instance to the bot

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
    if bot.server_instance:
        bot.server_instance.pause_alerts()
    else:
        send_telegram_alert("⚠️ *No ServerManager instance available.*")

@bot.message_handler(commands=["resume"])
def handle_resume(msg):
    if bot.server_instance:
        bot.server_instance.resume_alerts()
    else:
        send_telegram_alert("⚠️ *No ServerManager instance available.*")
# 🛠️ Command: /set_sr 0.25
@bot.message_handler(commands=["set_sr"])
def handle_set_sr(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["tolerance"] = value
        send_telegram_alert(f"⚙️ *SR tolerance* updated to `{value}`")
        if server_instance:
            try:
                server_instance.sync_remote_sr(sr_config)
                print("✅ SR sync successful")
                send_telegram_alert("✅ *SR config synced with server successfully.*")
            except Exception as e:
                print(f"🚫 Failed to sync SR config: {e}")
                send_telegram_alert(f"⚠️ *SR sync failed:* `{e}`")
        else:
            send_telegram_alert("⚠️ *No server instance available for SR sync.*")

    except:
        send_telegram_alert("⚠️ Usage: `/set_sr 2.5`")

# 📌 Command: /set_support 1920.5
@bot.message_handler(commands=["set_support"])
def handle_add_support(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["support"].append(value)
        send_telegram_alert(f"📌 *Support level* added: `{value}`")
        if server_instance:
            try:
                server_instance.sync_remote_sr(sr_config)
                print("✅ SR sync successful")
                send_telegram_alert("✅ *SR config synced with server successfully.*")
            except Exception as e:
                print(f"🚫 Failed to sync SR config: {e}")
                send_telegram_alert(f"⚠️ *SR sync failed:* `{e}`")
        else:
            send_telegram_alert("⚠️ *No server instance available for SR sync.*")

    except:
        send_telegram_alert("⚠️ Usage: `/set_support 1920.5`")

# 📌 Command: /set_resistance 1975.0
@bot.message_handler(commands=["set_resistance"])
def handle_add_resistance(msg):
    try:
        value = float(msg.text.split()[1])
        sr_config["resistance"].append(value)
        send_telegram_alert(f"📍 *Resistance level* added: `{value}`")
        if server_instance:
            try:
                server_instance.sync_remote_sr(sr_config)
                print("✅ SR sync successful")
                send_telegram_alert("✅ *SR config synced with server successfully.*")
            except Exception as e:
                print(f"🚫 Failed to sync SR config: {e}")
                send_telegram_alert(f"⚠️ *SR sync failed:* `{e}`")
        else:
            send_telegram_alert("⚠️ *No server instance available for SR sync.*")


    except:
        send_telegram_alert("⚠️ Usage: `/set_resistance 1975.0`")

# 📊 Command: /status
@bot.message_handler(commands=["status"])
def handle_status(msg):
    if bot.server_instance:
        status_text = bot.server_instance.get_status_payload()
        send_telegram_alert(status_text)
    else:
        send_telegram_alert("⚠️ *No server instance linked. Cannot fetch status.*")
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