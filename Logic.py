from datetime import datetime

from numpy.ma.core import resize

from  support import CandleFetcher
class Reversal:
    def __init__(self):
        self.consolidation_count = 0
        self.last_consolidation = None
        self.sr=SRManager(self)
        self.fetcher = CandleFetcher()

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

        if upper > lower  and all(directions) and any(s >= 2 for s in sizes):
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

        if lower >upper and all(directions) and any(s >= 2 for s in sizes):
            close_curr = float(next_two[-1]["close"])
            lows = [float(c["low"]) for c in next_two]
            size = round(close_curr - min(lows), 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔺 Upward Reversal (wick) at {ts}, size: ${size}"
        return None

    def is_pullback_reversal(self, next_two,initial_direction):
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
        open_first = last_three[0].get("open")
        close_last = last_three[-1].get("close")
        if not isinstance(open_first,(int,float)) or not isinstance(close_last,(int,float)):
            print("🚫 Invalid candle data for consolidation check.")
            return None
        net_move = abs(close_last - open_first)
        if net_move < 1:
            self.consolidation_count += 1
            if self.consolidation_count >=4 and not self.consolidation_triggered:
                self.consolidation_triggered = True
                self.consolidation_count=0
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                return f"⏸️ consolidation detected at {ts}, range: ${round(net_move, 2)}"
        else:
            self.consolidation_count = 0
            self.consolidation_triggered=False
        return None


class SRManager:
    def get_status_payload(self):
        status ="🔴 paused" if self.server.paused else "🟢 active"

        sr_config = {
            "tolerance": self.tolerance,
            "support": self.support,
            "resistance": self.resistance
        }
        tolerance = sr_config["tolerance"]

        support = sr_config["support"]
        resistance = sr_config["resistance"]

        payload = (
            f"📊 *System Status*\n"
            f"- Alerts: {status}\n"
            f"- Tolerance: `{tolerance}`\n"
            f"- Support Zones: `{', '.join(map(str, support)) or 'None'}`\n"
            f"- Resistance Zones: `{', '.join(map(str, resistance)) or 'None'}`"
        )
        return payload
    def __init__(self,server):
        self.support, self.resistance = [], []
        self.last_color=None
        self.red_candles, self.green_candles = [], []
        self.server=server
        self.fetcher=CandleFetcher()
        self.candle_size=[]
        self.tolerance = 3.0  # Default tolerance for SR breaks
        self.bounces = {"support": [], "resistance": []}
        # Track break types (for internal insight, optional)
        self.breaks = {
            "support": {"doji": 0, "momentum": 0, "high_volatility": 0},
            "resistance": {"doji": 0, "momentum": 0, "high_volatility": 0}
        }

        # Buffer of break sizes per zone
        self.break_buffer_detailed = {
            "support": {},      # Format: {zone_price: [size1, size2, ...]}
            "resistance": {}
        }

    def init_zones(self):
        print("📌 Enter SR levels (up to 4 each):")
        for i in range(4):
            s = input(f"Support {i+1}: ").strip()
            if s: self.support.append(float(s))
            r = input(f"Resistance {i+1}: ").strip()
            if r: self.resistance.append(float(r))

    def classify(self, size):
        return "doji" if abs(size) < 1 else "momentum" if abs(size) <= 5 else "high_volatility"

    def store_candle(self,size,Max_history=20):
        self.candle_size.append(size)
        if len(self.candle_size) > Max_history:
            self.candle_size.pop(0)

    def store_consecutive_candle(self, size, color):
        if color == "green":
            if self.last_color == "red":
                self.red_candles=[]
            self.green_candles.append(size)

        elif color == "red":
            if self.last_color =="green":
                self.red_candles=[]
            self.red_candles.append(size)

        else:
            print(f"doji: {color} and size {size}")

        self.last_color = color

    def get_nearest_zone(self, zone_type, price):
        zones = self.support if zone_type == "support" else self.resistance
        if not zones:
            print("🚫 No zones defined.")
            return None
        nearest = min(zones, key=lambda z: abs(z - price))
        return nearest

    def check_break(self, price, size, direction,):
        if direction == "down":
            zone_type = "support"
        elif direction == "up":
            zone_type = "resistance"
        else:
            print("🚫 Invalid direction for SR check.")
            return None

        zone_price = self.get_nearest_zone(zone_type, price)
        if zone_price is None:
            print("🚫 No nearest zone found.")
            return None

        effective_size = abs(size) if zone_type == "support" else size

        broken = (
            price < zone_price - self.tolerance if zone_type == "support"
            else price > zone_price + self.tolerance
        )

        if broken and effective_size > 2:
            category = self.classify(effective_size)
            self.breaks[zone_type][category] += 1
            self.break_buffer_detailed[zone_type].setdefault(zone_price, []).append(effective_size)
            msg=f"🚨 {zone_type.capitalize()}{zone_price} Broken! by Price: {price},  Size: ${round(effective_size,2)}, Type: {category}"
            return msg
        elif not broken:
            return None
