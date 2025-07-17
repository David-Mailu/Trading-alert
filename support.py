import time
from datetime import datetime
from pytz import timezone
from Feed import get_xauusd_15min_candles
from Telegramalert import send_telegram_alert
from requests.exceptions import RequestException
# 🕒 Market Schedule Handler
class MarketSchedule:
    def __init__(self, debug=False):
        self.debug = debug

    def is_market_open(self):
        eat = timezone("Africa/Nairobi")
        now = datetime.now(eat)
        print(f"🕒 Market check: {now.strftime('%A %H:%M')}")
        if self.debug:
            print("🧪 Debug ON: Skipping market hours check.")
            return True

        wd, hr, min = now.weekday(), now.hour, now.minute
        return not (
            wd in [5, 6] or
            (wd == 4 and (hr > 23 or (hr == 23 and min >= 45))) or
            (wd == 0 and hr < 2)
        )

    def in_maintenance(self):
        eat = timezone("Africa/Nairobi")
        return datetime.now(eat).hour == 0

# 📡 Candle Fetcher with Retry Logic
class CandleFetcher:
    def pull(self):
        retry_schedule = [10, 600, 1800, 3600]
        for i, delay in enumerate(retry_schedule, 1):
            try:
                candle = get_xauusd_15min_candles()
                if candle and "open" in candle and "close" in candle:
                    return candle
                print(f"🧭 Incomplete data: {candle}")
            except RequestException as e:
                print(f"📡 Network error {i}: {e}")
            except Exception as e:
                print(f"⚠️ Unexpected error {i}: {e}")
            print(f"🕒 Retrying in {delay} sec...")
            time.sleep(delay)
        print("📴 Connection failed.")
        return None


# 📋 Alert Logger
class AlertLogger:
    def __init__(self, conn): self.conn = conn

    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        full = f"[{ts}] {msg}"
        print(full)
        self.conn.sendall(full.encode('utf-8'))
        send_telegram_alert(full)
