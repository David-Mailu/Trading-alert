from bot import (sr_config, send_telegram_alert, )
from telebot import TeleBot
from Server import SmartServer

class SmartBot(TeleBot):
    def __init__(self, token, server_instance):
        super().__init__(token)
        self.server_instance = server_instance
bot = SmartBot("7701018588:AAEjcMhWCAmd-pgYtgSGgXaFUHpJoK8KO6k", server_instance)


def trigger_alert_if_active(candle_data):
    """
    Checks system state and sends alert if allowed.
    Expects candle_data to contain 'open', 'close', and 'timestamp'.
    """

    if not server_instance.alerts_active:
        print("🔕 Alert skipped: system is paused.")
        return

    open_ = candle_data["open"]
    close = candle_data["close"]
    timestamp = candle_data.get("timestamp", "N/A")
    size = abs(close - open_)

    message = (
        f"📈 *New Candle Triggered*\n"
        f"- Time: `{timestamp}`\n"
        f"- Open: `{open_}`\n"
        f"- Close: `{close}`\n"
        f"- Size: `{size}`\n"
        f"- SR Tolerance: `{sr_config['tolerance']}`"
    )

    send_telegram_alert(message)