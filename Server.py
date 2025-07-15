import socket, time
from datetime import datetime, timedelta
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

# 📌 Support/Resistance Manager
class SRManager:
    def __init__(self):
        self.support, self.resistance = [], []
        self.bounces = {"support": [], "resistance": []}
        self.breaks = {
            "support": {"doji": 0, "momentum": 0, "high_volatility": 0},
            "resistance": {"doji": 0, "momentum": 0, "high_volatility": 0}
        }

    def init_zones(self):
        print("📌 Enter SR levels (up to 2 each):")
        for i in range(2):
            s = input(f"Support {i+1}: ").strip()
            if s: self.support.append(float(s))
            r = input(f"Resistance {i+1}: ").strip()
            if r: self.resistance.append(float(r))

    def update_zone(self, price, direction):
        zones = self.support if direction == "up" else self.resistance
        zones[:] = [z for z in zones if abs(z - price) > 5]
        if len(zones) >= 4: zones.pop(0)
        zones.append(price)

    def classify(self, size):
        return "doji" if size < 2 else "momentum" if size <= 5 else "high_volatility"

    def track_break(self, zone_type, candle_type):
        self.breaks[zone_type][candle_type] += 1

    def nearest_zone(self, price, zone_type):
        zones = self.support if zone_type == "support" else self.resistance
        return min(zones, key=lambda z: abs(z - price)) if zones else None

    def record_bounce(self, typ, zone_price, price):
        if abs(price - zone_price) <= 5:
            self.bounces[typ].append(price)
            if len(self.bounces[typ]) > 2: self.bounces[typ].pop(0)

    def report_breaks(self, zone_type):
        bt = self.breaks[zone_type]
        total = sum(bt.values())
        if total:
            msg = f"🔔 {zone_type.capitalize()} broken by " + ", ".join(f"{v}×{k}" for k,v in bt.items() if v)
            self.breaks[zone_type] = {k: 0 for k in bt}
            return msg
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
        with open("server_alerts_log.txt", "a", encoding="utf-8") as f:
            f.write(full + "\n")

# 🧠 Smart Alert Server
class SmartServer:
    def __init__(self, debug=False):
        self.debug = debug
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.bind(('::1', 65432))
        self.sock.listen()
        print("🧠 Server online (IPv6). Waiting for connection...")
        self.conn, addr = self.sock.accept()
        print(f"🔗 Connected to {addr}")

        self.market = MarketSchedule(debug=debug)
        self.fetcher = CandleFetcher()
        self.sr = SRManager()
        self.log = AlertLogger(self.conn)
        self.reversal = Reversal()
        self.reversal_buffer = []
        self.prev_dir = None
        self.prev_size = None
        self.last_break = None

    def wait_next_quarter(self):
        now = datetime.now()
        minute = ((now.minute // 15 + 1) * 15) % 60
        hour = (now.hour + (1 if minute == 0 else 0)) % 24
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        sleep = (next_time - now).total_seconds()
        print(f"⏳ Next run at {next_time.strftime('%H:%M')} ({int(sleep)}s)")
        time.sleep(sleep)

    def initialize(self):
        if not self.market.is_market_open():
            print("📴 Market closed. Exit.")
            return False
        self.sr.init_zones()
        d = input("📈 Previous direction (up/down): ").strip()
        self.prev_dir = d if d in ["up", "down"] else None
        try:
            self.prev_size = float(input("💡 Previous candle size: ").strip())
        except:
            self.prev_size = None
        return True

    def start(self):
        if not self.initialize(): return
        try:
            while True:
                self.wait_next_quarter()
                if self.market.in_maintenance():
                    print("😴 Maintenance window (12AM–1AM). Sleeping...")
                    time.sleep(3600)
                    continue

                candle = self.fetcher.pull()
                open_, close = float(candle["open"]), float(candle["close"])
                size, price = abs(close - open_), close
                direction = "up" if close > open_ else "down"
                # 🧠 Add to reversal buffer
                self.reversal_buffer.append(candle)
                if len(self.reversal_buffer) > 3:
                    self.reversal_buffer.pop(0)

                # 🔄 Reversal Logic
                if len(self.reversal_buffer) == 3:
                    base, next1, next2 = self.reversal_buffer
                    msg = self.reversal.is_downward_reversal(base, [next1, next2])
                    if not msg:
                        msg = self.reversal.is_upward_reversal(base, [next1, next2])
                    if not msg:
                        msg = self.reversal.is_pullback_reversal("up" if base["close"] > base["open"] else "down",
                                                                 [next1, next2])
                    if msg:
                        self.log.log(msg)

                    # ⏸️ Consolidation Check
                    msg = self.reversal.detect_consolidation(self.reversal_buffer)
                    if msg:
                        self.log.log(msg)

                if not candle: continue

                open_, close = float(candle["open"]), float(candle["close"])
                size, price = abs(close - open_), close
                direction = "up" if close > open_ else "down"

                self.sr.update_zone(price, direction)
                for typ in ["support", "resistance"]:
                    zone = self.sr.nearest_zone(price, typ)
                    if zone:
                        self.sr.record_bounce(typ, zone, price)
                        broken = (price - zone > 5 if typ == "resistance" else zone - price > 5)
                        if broken:
                            ctype = self.sr.classify(size)
                            self.sr.track_break(typ, ctype)

                if all(len(self.sr.bounces[t]) >= 2 for t in ["support", "resistance"]):
                    msg = f"📊 Consolidation detected between Support ≈ ${self.sr.nearest_zone(price, 'support')} and Resistance ≈ ${self.sr.nearest_zone(price, 'resistance')}"
                    self.log.log(msg)
                    self.sr.bounces = {"support": [], "resistance": []}

                for typ in ["support", "resistance"]:
                    msg = self.sr.report_breaks(typ)
                    if msg: self.log.log(msg)

                if size > 5:
                    self.log.log(f"⚡ High Volatility! Size: ${size}")
                elif 2 <= size <= 5:
                    similar = self.prev_size and abs(size - self.prev_size) < 0.5 and direction == self.prev_dir
                    clustered = self.last_break and datetime.now() - self.last_break < timedelta(minutes=30)
                    if similar or clustered:
                        print("🚫 Skipped: Similar candle or recent SR break.")
                        self.prev_dir, self.prev_size = direction, size
                        continue
                    zone = self.sr.nearest_zone(price, "resistance")
                    if zone and price > zone:
                        msg = f"📈 Resistance broken near ${zone} ➞ ${price}"
                        self.last_break = datetime.now()
                        self.log.log(msg)
                    elif (zone := self.sr.nearest_zone(price, "support")) and price < zone:
                        msg = f"📉 Support broken near ${zone} ➞ ${price}"
                        self.last_break = datetime.now()
                        self.log.log(msg)
                    else:
                         msg = f"💥 Momentum candle: ${size}"
                         self.log.log(msg)


                self.prev_dir, self.prev_size = direction, size
        except KeyboardInterrupt:
            print("🛑 Server interrupted.")
        except Exception as e:
            print(f"💥 Uncaught error: {e}")
        finally:
            print("🔌 Closing server...")
            self.conn.close()
            self.sock.close()


class Reversal:
    def __init__(self):
        self.consolidation_count = 0
        self.last_consolidation = None

    def get_wicks(self, candle):
        open_, close = float(candle["open"]), float(candle["close"])
        high, low = float(candle["high"]), float(candle["low"])

        if close < open_:
            upper_wick = high - open_
            lower_wick = close - low
        else:
            upper_wick = high - close
            lower_wick = low - open_

        return upper_wick, lower_wick

    def is_downward_reversal(self, candle, next_two):
        upper, lower = self.get_wicks(candle)
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two]

        if upper >= 1 and lower <= 0.5 and all(directions) and any(s >= 2 for s in sizes):
            high = float(candle["high"])
            close_last = float(next_two[-1]["close"])
            size = round(high - close_last, 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔻 Downward Reversal (wick) at {ts}, size: ${size}"
        return None

    def is_upward_reversal(self, candle, next_two):
        upper, lower = self.get_wicks(candle)
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) > float(c["open"]) for c in next_two]

        if lower >= 1 and upper <= 0.5 and all(directions) and any(s >= 2 for s in sizes):
            close_curr = float(next_two[-1]["close"])
            lows = [float(c["low"]) for c in next_two]
            size = round(close_curr - min(lows), 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔺 Upward Reversal (wick) at {ts}, size: ${size}"
        return None

    def is_pullback_reversal(self, initial_direction, next_two):
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two] if initial_direction == "up" else \
                     [float(c["close"]) > float(c["open"]) for c in next_two]

        if all(directions) and any(s >= 2 for s in sizes):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            if initial_direction == "up":
                close_last = float(next_two[-1]["close"])
                high = max(float(c["high"]) for c in next_two)
                size = round(high - close_last, 2)
                return f"🔻 Pullback Reversal (Down) at {ts}, size: ${size}"
            else:
                close_last = float(next_two[-1]["close"])
                low = min(float(c["low"]) for c in next_two)
                size = round(close_last - low, 2)
                return f"🔺 Pullback Reversal (Up) at {ts}, size: ${size}"
        return None

    def detect_consolidation(self, last_three):
        open_first = float(last_three[0]["open"])
        close_last = float(last_three[-1]["close"])
        net_move = abs(close_last - open_first)
        if net_move < 3:
            self.consolidation_count += 1
            if self.consolidation_count <= 4:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                return f"⏸️ Consolidation detected at {ts}, range: ${round(net_move, 2)}"
        else:
            self.consolidation_count = 0
        return None



if __name__ == "__main__":
    try:
        server = SmartServer(debug=False)
        server.start()
    except Exception as e:
        print(f"🚨 Fatal error in orchestrator: {e}")