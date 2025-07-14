import socket
import time
from datetime import datetime, timedelta
from Feed import get_xauusd_15min_candles
from Telegramalert import send_telegram_alert
from pytz import timezone
from requests.exceptions import RequestException

# 🕒 Market Schedule
def markets_open_now():
    eat = timezone("Africa/Nairobi")
    now = datetime.now(eat)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    if weekday == 5 or weekday == 6:
        return False
    elif weekday == 4 and (hour > 23 or (hour == 23 and minute >= 45)):
        return False
    elif weekday == 0 and hour < 2:
        return False
    return True

# 😴 Maintenance Sleep Window
def in_sleep_window():
    eat = timezone("Africa/Nairobi")
    now = datetime.now(eat)
    return now.weekday() in range(0, 5) and now.hour == 0

# 📡 Resilient Data Pull
def resilient_data_pull():
    retry_schedule = [10, 600, 1800, 3600]
    for attempt, delay in enumerate(retry_schedule, start=1):
        try:
            candle = get_xauusd_15min_candles()
            if candle and "open" in candle and "close" in candle:
                return candle
            else:
                print(f"🧭 Twelve Data API failed: Incomplete candle data {candle}")
        except RequestException as e:
            print(f"📡 Network error attempt {attempt}: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error attempt {attempt}: {e}")

        print(f"🕒 Retrying in {delay // 60 if delay >= 60 else delay} {'min' if delay >= 60 else 'sec'}...")
        time.sleep(delay)

    print("📴 Poor internet connection. Program terminated.")
    return None

# 📌 Manual SR Setup
support_levels = []
resistance_levels = []
MAX_ZONES = 4
BOUNCE_DISTANCE = 5
RANGE_THRESHOLD = 2
bounce_records = {"support": [], "resistance": []}

def initialize_zones():
    print("📌 Optional SR Setup — Enter up to 2 support/resistance levels (press Enter to skip):")
    for i in range(2):
        s = input(f"Support {i+1}: ").strip()
        if s:
            support_levels.append(float(s))
        r = input(f"Resistance {i+1}: ").strip()
        if r:
            resistance_levels.append(float(r))

def update_zones(price, direction, last_direction):
    zone_list = support_levels if direction == "up" else resistance_levels
    redundant = [z for z in zone_list if abs(z - price) <= BOUNCE_DISTANCE]
    if redundant:
        zone_list.remove(redundant[0])
    if len(zone_list) >= MAX_ZONES:
        zone_list.pop(0)
    zone_list.append(price)

def get_nearest_zone(price, zones):
    return min(zones, key=lambda z: abs(z - price)) if zones else None

def record_bounce(zone_type, zone_price, price):
    if abs(price - zone_price) <= BOUNCE_DISTANCE:
        bounce_records[zone_type].append(price)
        if len(bounce_records[zone_type]) > RANGE_THRESHOLD:
            bounce_records[zone_type].pop(0)

def wait_until_next_quarter():
    now = datetime.now()
    minute = (now.minute // 15 + 1) * 15
    if minute == 60:
        next_time = now.replace(hour=(now.hour + 1) % 24, minute=0, second=0, microsecond=0)
    else:
        next_time = now.replace(minute=minute, second=0, microsecond=0)
    wait_seconds = (next_time - now).total_seconds()
    print(f"⏳ Waiting until {next_time.strftime('%H:%M')} ({int(wait_seconds)}s)...")
    time.sleep(wait_seconds)

def log_alert(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open("server_alerts_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(formatted + "\n")

# 🚀 Startup Checks
if not markets_open_now():
    print("📴 Markets closed. Program will now exit.")
    exit()

initialize_zones()

# 🌐 Dual-stack socket setup (IPv6 preferred, fallback handled via client)
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
server_socket.bind(('::1', 65432))
server_socket.listen()
print("🧠 Smart server online (IPv6)...")

conn, addr = server_socket.accept()
print(f"🔗 Connected to {addr}")

prev_direction = None
prev_candle_size = None
last_sr_break_time = None

try:
    while True:
        wait_until_next_quarter()

        if in_sleep_window():
            print("😴 Sleeping for maintenance (12AM–1AM EAT)...")
            time.sleep(3600)
            continue

        candle = resilient_data_pull()
        if not candle:
            continue

        open_price = float(candle["open"])
        close_price = float(candle["close"])
        current_price = close_price
        candle_size = abs(close_price - open_price)
        direction = "up" if close_price > open_price else "down"

        update_zones(current_price, direction, prev_direction)
        nearest_support = get_nearest_zone(current_price, support_levels)
        nearest_resistance = get_nearest_zone(current_price, resistance_levels)

        if nearest_support and current_price > nearest_support:
            record_bounce("support", nearest_support, current_price)
        if nearest_resistance and current_price < nearest_resistance:
            record_bounce("resistance", nearest_resistance, current_price)

        if (
            len(bounce_records["support"]) >= RANGE_THRESHOLD and
            len(bounce_records["resistance"]) >= RANGE_THRESHOLD
        ):
            message = f"📊 Consolidation Detected between Support ≈ ${nearest_support} and Resistance ≈ ${nearest_resistance}"
            conn.sendall(message.encode('utf-8'))
            send_telegram_alert(message)
            log_alert(message)
            bounce_records["support"].clear()
            bounce_records["resistance"].clear()
            prev_direction = direction
            continue

        timestamp = datetime.now()
        if candle_size >= 4:
            message = f"⚡ High Volatility! Size: ${candle_size}"
        elif candle_size >= 2:
            similar_candle = (
                prev_candle_size and
                abs(candle_size - prev_candle_size) < 0.5 and
                direction == prev_direction
            )
            sr_blocked = (
                last_sr_break_time and
                (timestamp - last_sr_break_time < timedelta(minutes=30))
            )

            if similar_candle or sr_blocked:
                print("🚫 Skipped: Similar candle or clustered SR break.")
                prev_direction = direction
                prev_candle_size = candle_size
                continue

            if nearest_resistance and current_price > nearest_resistance:
                message = f"📈 Resistance broken near ${nearest_resistance} ➞ ${current_price}"
                last_sr_break_time = timestamp
            elif nearest_support and current_price < nearest_support:
                message = f"📉 Support broken near ${nearest_support} ➞ ${current_price}"
                last_sr_break_time = timestamp
            else:
                message = f"💥 Momentum candle: ${candle_size}"
        else:
            prev_direction = direction
            prev_candle_size = candle_size
            continue

        conn.sendall(message.encode('utf-8'))
        send_telegram_alert(message)
        log_alert(message)

        prev_direction = direction
        prev_candle_size = candle_size

except KeyboardInterrupt:
    print("🛑 Smart server closed by user.")
    conn.close()
    server_socket.close()
    exit()