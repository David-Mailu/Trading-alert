# server.py
import socket
import time
from datetime import datetime, timedelta
from Feed import get_xauusd_price  # Capital "F" as per your file name
from Telegramalert import send_telegram_alert

SUPPORT = 3250
RESISTANCE = 3345
prev_price = 3305
prev_candle_size = 1
prev_direction = None
last_sr_break_time = None
monitoring_active = True

candle_history = []
MAX_HISTORY = 10

def get_direction(current, previous):
    return "up" if current > previous else "down"

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

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 65432))
server_socket.listen()
print("🧠 Smart server online...")

conn, addr = server_socket.accept()
print(f"🔗 Connected to {addr}")

while True:
    wait_until_next_quarter()
    current_price = get_xauusd_price()
    if current_price is None:
        print("❌ Skipping update due to API error.")
        continue

    timestamp = datetime.now()
    candle_size = abs(current_price - prev_price)
    direction = get_direction(current_price, prev_price)

    candle_history.append({
        "size": candle_size,
        "direction": direction,
        "price": current_price
    })
    if len(candle_history) > MAX_HISTORY:
        candle_history.pop(0)

    if not monitoring_active:
        wick_reversal = (
            prev_direction and
            candle_size < prev_candle_size and
            direction != prev_direction and
            candle_size >= 2
        )

        reversal = False
        if len(candle_history) >= 2:
            last = candle_history[-1]
            second_last = candle_history[-2]
            if (
                last["size"] >= 2 and
                second_last["size"] >= 2 and
                last["direction"] != second_last["direction"]
            ):
                reversal = True

        fading = False
        recent_dojis = [c for c in candle_history[-4:] if c["size"] <= 1]
        if len(recent_dojis) == 4:
            fading = True

        if candle_size >= 4:
            message = f"⚡ High Volatility Detected (Paused)! Size: ${candle_size}"
            conn.sendall(message.encode('utf-8'))
            send_telegram_alert(message)
        elif wick_reversal:
            message = f"🔄 Wick Reversal Triggered at ${current_price}"
            conn.sendall(message.encode('utf-8'))
            send_telegram_alert(message)
        elif reversal:
            message = f"🔁 Momentum Flip: {second_last['direction']} ➡ {last['direction']} at ${current_price}"
            conn.sendall(message.encode('utf-8'))
            send_telegram_alert(message)
        elif fading:
            message = f"😶 Consolidation Zone Detected: 4 Dojis near ${current_price}"
            conn.sendall(message.encode('utf-8'))
            send_telegram_alert(message)
        else:
            print("⏸ Monitoring paused — no reversal condition met.")

        prev_price = current_price
        prev_direction = direction
        prev_candle_size = candle_size
        continue

    # 💥 Active Monitoring Mode
    if candle_size >= 4:
        message = f"⚡ High Volatility! Size: ${candle_size}"
        conn.sendall(message.encode('utf-8'))
        send_telegram_alert(message)

    elif candle_size >= 2:
        similar_candle = (
            abs(candle_size - prev_candle_size) < 0.5 and
            direction == prev_direction
        )
        sr_blocked = (
            last_sr_break_time and
            (timestamp - last_sr_break_time < timedelta(minutes=30))
        )

        if similar_candle:
            print("🚫 Skipped: Similar candle detected.")
        elif sr_blocked:
            print("🚫 Skipped: SR break clustering.")
        else:
            if current_price > RESISTANCE:
                message = f"📈 Resistance broken at ${current_price}"
                conn.sendall(message.encode('utf-8'))
                send_telegram_alert(message)
                last_sr_break_time = timestamp
            elif current_price < SUPPORT:
                message = f"📉 Support broken at ${current_price}"
                conn.sendall(message.encode('utf-8'))
                send_telegram_alert(message)
                last_sr_break_time = timestamp
            else:
                message = f"💥 Momentum candle: ${candle_size}"
                conn.sendall(message.encode('utf-8'))
                send_telegram_alert(message)

        prev_candle_size = candle_size
        prev_direction = direction

    prev_price = current_price