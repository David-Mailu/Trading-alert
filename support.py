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
        sleep_duration = (target_time - now).total_seconds()

        print(f"⏳ Next run at {target_time.strftime('%H:%M:%S')} ({int(sleep_duration)}s)")
        if self.shutdown_event and self.shutdown_event.wait(timeout=sleep_duration):
            print("🛑 Shutdown signal received during wait.")
            return False
        return True

    def __init__(self, debug=False, shutdown_event=None):
        self.shutdown_event = shutdown_event
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
class Reversal:
    def __init__(self):
        self.consolidation_count = 0
        self.last_consolidation = None
        self.consolidation_triggered=False

    def get_wicks(self, candle):
        open_, close = float(candle["open"]), float(candle["close"])
        high, low = float(candle["high"]), float(candle["low"])

        if close < open_:
            upper_wick = high - open_
            lower_wick = close - low
        elif close > open_:
            upper_wick = high - close
            lower_wick = low - open_
        else:
            print("neutral candle - no wicks")
            return 0, 0
        return upper_wick, lower_wick


    def is_wick_reversal(self, candle, next_two,base_direction,tick_volume,ats_short,next1_direction):
        if base_direction not in ["up", "down"] :
            return None
        upper, lower = self.get_wicks(candle)
        if upper and lower is None:
            print("🚫 Invalid candle data for upward reversal check.")
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions_up = [float(c["close"]) > float(c["open"]) for c in next_two]
        direction_down = [float(c["close"]) < float(c["open"]) for c in next_two]

        if lower >upper and all(directions_up) and base_direction=="down" and next1_direction=="down" and any(s >= 0.7*ats_short for s in sizes):
            close_curr = float(next_two[-1]["close"])
            lows = [float(c["low"]) for c in next_two]
            size = round(close_curr - min(lows), 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔺 Upward Reversal (wick) at {ts}, size: ${size} and tick_volume: {tick_volume}"
        if upper > lower and all(direction_down) and base_direction == "up" and next1_direction=="up" and any(s >= ats_short for s in sizes):
            high = float(candle["high"])
            close_last = float(next_two[-1]["close"])
            size = round(high - close_last, 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔻 Downward Reversal (wick) at {ts}, size: ${size} and tick_volume: {tick_volume}"
        return None

    def is_pullback_reversal(self,next_two,base_direction,tick_volume,ats_short,next1_direction):
        if base_direction not in ["up", "down"] :
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two] if base_direction == "up" else \
                     [float(c["close"]) > float(c["open"]) for c in next_two]

        if all(directions) and any(s >=0.5*ats_short for s in sizes) and next1_direction==base_direction:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            if base_direction == "up":
                close_last = float(next_two[-1]["close"])
                high = max(float(c["high"]) for c in next_two)
                size = round(high - close_last, 2)
                return f"🔻 Pullback Reversal (Down) at {ts}, size: ${size} and tick_volume: {tick_volume}"
            else:
                close_last = float(next_two[-1]["close"])
                low = min(float(c["low"]) for c in next_two)
                size = round(close_last - low, 2)
                return f"🔺 Pullback Reversal (Up) at {ts}, size: ${size} and tick_volume: {tick_volume}"
        return None

    def engulfing_reversal(self, last_three, base_direction,tick_volume,ats_short):
        """
        Detects bullish or bearish engulfing reversal based on last three candles and base direction.
        Returns a formatted string if reversal is detected, else None.
        """

        if len(last_three) != 3:
            return None  # Ensure exactly three candles are passed

        c1, c2, c3 = last_three  # c1 = next1, c2 = next2, c3 = next3

        # Direction helpers
        def is_up(c):
            return float(c["close"]) > float(c["open"])

        def is_down(c):
            return float(c["close"]) < float(c["open"])

        def body_size(c):
            return abs(float(c["close"]) - float(c["open"]))

        # Sizes
        size_c2 = body_size(c2)
        size_c3 = body_size(c3)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 🔻 Bearish Engulfing Reversal
        if base_direction == "up" and is_up(c1) and is_up(c2) and is_down(c3):
            if size_c3 > size_c2 and size_c3 >= 1.5*ats_short:
                return f"🔻 Bearish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)} and tick_volume: {tick_volume}"

        # 🔺 Bullish Engulfing Reversal
        if base_direction == "down" and is_down(c1) and is_down(c2) and is_up(c3):
            if size_c3 > size_c2 and size_c3 >=1.5*ats_short:
                return f"🔺 Bullish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)} and tick_volume: {tick_volume}"

        return None

    def reversal(self, store_candle, recent_direction, tick_volume,ats):
        if len(store_candle) < 5:
            print("🚫 Not enough candles to evaluate reversal.")
            return None

        base, next1, next2, next3, next4 = store_candle[-5:]

        try:
            # Direction and size calculations
            candles = [base, next1, next2, next3, next4]
            directions = []
            sizes = []

            for i, candle in enumerate(candles):
                open_price = float(candle["open"])
                close_price = float(candle["close"])
                direction = "up" if close_price > open_price else "down"
                size = abs(close_price - open_price)
                directions.append(direction)
                sizes.append(size)

            # Override direction for most recent candle
            directions[-1] = recent_direction

            # Shared size metric for output
            total_size = abs(float(next4["close"]) - float(next1["close"]))

        except (KeyError, TypeError, ValueError):
            print("🚫 Invalid candle structure or non-numeric values.")
            return None

        # ATR-based downward reversal
        if (
                directions[0] == "down" and sizes[0] >= 0.5*ats and
                directions[1] == "down" and sizes[1] >= 0.5*ats and
                directions[2] == "up" and sizes[2] >= 1.5*ats and
                directions[3] == "down" and sizes[3] >= 0.1*ats and
                directions[4] == "down" and sizes[4] >= 0.5*ats
        ):
            return f"🔽  downward reversal detected size: ${round(total_size, 2)} and tick_volume: {tick_volume}"

        # ATR-based upward reversal
        if (
                directions[0] == "up" and sizes[0] >=0.5 and
                directions[1] == "up" and sizes[1] >= 0.5 and
                directions[2] == "down" and sizes[2] >= 4 and
                directions[3] == "up" and sizes[3] >=0.1 and
                directions[4] == "up" and sizes[4] >= 0.5
        ):
            return f"🔼  upward reversal detected size: ${round(total_size, 2)} and tick_volume: {tick_volume}"

        # Legacy pattern (optional fallback)
        if (
                directions[0] == "down" and
                directions[1] == "down" and
                directions[2] == "up" and
                directions[3] == "down" and
                directions[4] == "up" and
                sizes[4] >= 3
        ):
            return f"🔼 legacy upward reversal detected size: ${round(total_size, 2)} and tick_volume: {tick_volume}"

        if (
                directions[0] == "up" and
                directions[1] == "up" and
                directions[2] == "down" and
                directions[3] == "up" and
                directions[4] == "down" and
                sizes[4] >= 3
        ):
            return f"🔽 legacy downward reversal detected size: ${round(total_size, 2)} and tick_volume: {tick_volume}"

        return None

