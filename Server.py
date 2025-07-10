import socket
import time
from datetime import datetime, timedelta

SUPPORT = 3250
RESISTANCE = 3345
prev_price = 3305
prev_candle_size = 1
prev_direction = None
last_sr_break_time = None
monitoring_active = True

def get_direction(current, previous):
    return "up" if current > previous else "down"

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 65432))
server_socket.listen()
print("🧠 Smart server online...")

conn, addr = server_socket.accept()
print(f"🔗 Connected to {addr}")

while True:
    command = input("Trade status (entered/resume/skip): ").lower()
    if command == "entered":
        monitoring_active = False
        conn.sendall("🚫 Monitoring paused.".encode('utf-8'))
    elif command == "resume":
        monitoring_active = True
        conn.sendall("🔄 Monitoring resumed.".encode('utf-8'))

    current_price = float(input("Enter XAUUSD price: "))
    timestamp = datetime.now()
    candle_size = abs(current_price - prev_price)
    direction = get_direction(current_price, prev_price)

    # 🚨 Volatility always triggers
    if candle_size >= 4:
        conn.sendall(f"⚡ High Volatility! ${candle_size}".encode('utf-8'))

    # 🧠 Noise filter — avoid consecutive similar alerts
    elif monitoring_active and candle_size >= 2:
        similar_candle = (abs(candle_size - prev_candle_size) < 0.5) and (direction == prev_direction)

        # ⏱ SR clustering blocker — don't alert more than once every 30 mins
        sr_blocked = last_sr_break_time and (timestamp - last_sr_break_time < timedelta(minutes=30))

        if similar_candle:
            print("🚫 Skipped: Similar candle detected.")
        elif sr_blocked:
            print("🚫 Skipped: SR break clustering.")
        else:
            if current_price > RESISTANCE:
                conn.sendall(f"📈 Resistance broken at ${current_price}".encode('utf-8'))
                last_sr_break_time = timestamp
            elif current_price < SUPPORT:
                conn.sendall(f"📉 Support broken at ${current_price}".encode('utf-8'))
                last_sr_break_time = timestamp
            else:
                conn.sendall(f"💥 Momentum candle detected: ${candle_size}".encode('utf-8'))

        prev_candle_size = candle_size
        prev_direction = direction

    prev_price = current_price
    time.sleep(1)