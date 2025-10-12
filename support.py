import time
import socket
from datetime import datetime,timedelta
from pytz import timezone
from Feed import get_xauusd_15min_candles
from bot import send_telegram_alert
from requests.exceptions import RequestException
# 🕒 Market Schedule Handler
class MarketSchedule:
    def wait_next_quarter(self, buffer_seconds=0.26):
        """
        Waits until buffer_seconds after the next quarter-hour mark.
        Ensures candle is finalized before fetching.
        """
        now = datetime.now()
        minute = ((now.minute // 15 + 1) * 15) % 60
        hour = (now.hour + (1 if minute == 0 else 0)) % 24

        # Next quarter-hour timestamp
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_time <= now:
            next_time+= timedelta(days=1)
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
            (wd == 0 and hr < 1)
        )

    def in_maintenance(self):
        eat = timezone("Africa/Nairobi")
        return datetime.now(eat).hour == 0

    def market_session(self):
        eat = timezone("Africa/Nairobi")
        now = datetime.now(eat)
        hr, min = now.hour, now.minute
        time_decimal = hr + min / 60

        # Define session windows in EAT (UTC+3)
        sessions = {
            "Asian": (3.0, 12.0),
            "London": (10.0, 19.0),
            "New York": (16.0, 25.0)  # Wraps past midnight
        }

        active_sessions = []
        for name, (start, end) in sessions.items():
            if start < end:
                if start <= time_decimal < end:
                    active_sessions.append(name)
            else:  # Handles wraparound (e.g., NY session)
                if time_decimal >= start or time_decimal < end - 24:
                    active_sessions.append(name)

        if not active_sessions:
            return "Closed"

        return " & ".join(active_sessions)
# 📡 Candle Fetcher with Retry Logic
class CandleFetcher:
    def pull(self):
        retry_schedule = [10,60,100,150,200,300,600,1800]
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

class AlertLogger:
    def __init__(self, conn, max_retries=3, retry_delay=1):
        self.conn = conn
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        full = f"[{ts}] {msg}"
        print(full)

        if self.conn:
            for attempt in range(1, self.max_retries + 1):
                try:
                    self.conn.sendall(full.encode('utf-8'))
                    break  # Success
                except Exception as e:
                    print(f"[Retry {attempt}] Socket send failed: {e}")
                    time.sleep(self.retry_delay)
            else:
                print("[ERROR] All retries failed. Falling back to Telegram.")

        send_telegram_alert(full)
