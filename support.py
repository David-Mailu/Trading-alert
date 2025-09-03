import time
from datetime import datetime,timedelta
from pytz import timezone
from Feed import get_xauusd_15min_candles
from bot import send_telegram_alert
from requests.exceptions import RequestException
# 🕒 Market Schedule Handler
class MarketSchedule:
    def wait_next_quarter(self, buffer_seconds=1):
        """
        Waits until buffer_seconds after the next quarter-hour mark.
        Ensures candle is finalized before fetching.
        """
        now = datetime.now()
        minute = ((now.minute // 15 + 1) * 15) % 60
        hour = (now.hour + (1 if minute == 0 else 0)) % 24

        # Next quarter-hour timestamp
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Add buffer to ensure candle finalization
        target_time = next_time + timedelta(seconds=buffer_seconds)
        sleep = (target_time - now).total_seconds()

        print(f"⏳ Next run at {target_time.strftime('%H:%M:%S')} ({int(sleep)}s)")
        time.sleep(sleep)

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
