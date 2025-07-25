from datetime import datetime
from  Feed import get_xauusd_15min_candles
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
        if net_move < 1:
            self.consolidation_count += 1
            if self.consolidation_count >= 6:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                return f"⏸️ A breakout detected at {ts}, range: ${round(net_move, 2)}"
        else:
            self.consolidation_count = 0
        return None


class SRManager:
    def get_status_payload(self):
        status = "🟢 active" if self.alerts_active else "🔴 paused"

        sr_config = self.sr.get_config()
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
    def __init__(self):
        self.support, self.resistance = [], []
        self.alerts_active = False
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
        return "doji" if size < 2 else "momentum" if size <= 5 else "high_volatility"

    def track_break(self, zone_type, candle_type):
        self.breaks[zone_type][candle_type] += 1

    def nearest_zone(self, price, zone_type):
        zones = self.support if zone_type == "support" else self.resistance
        return min(zones, key=lambda z: abs(z - price)) if zones else None

    def record_bounce(self, typ, zone_price, price):
        if abs(price - zone_price) <= 5:
            self.bounces[typ].append(price)
            if len(self.bounces[typ]) > 2:
                self.bounces[typ].pop(0)

    def is_valid_break(self, candle, zone_type, zone_price):
        open_, close = float(candle["open"]), float(candle["close"])
        direction = "up" if close > open_ else "down"
        price = close

        if zone_type == "support" and direction == "down":
            return price < zone_price and abs(price - zone_price) <= self.tolerance
        elif zone_type == "resistance" and direction == "up":
            return price > zone_price and abs(price - zone_price) <= self.tolerance
        return False

    def add_break(self, zone_type, zone_price, candle_size):
        buffer = self.break_buffer_detailed[zone_type]
        if zone_price not in buffer:
            buffer[zone_price] = []
        buffer[zone_price].append(candle_size)

    def report_strong_breaks(self, zone_type):
        buffer = self.break_buffer_detailed[zone_type]
        messages = []
        for zone_price, sizes in buffer.items():
            total = round(sum(sizes), 2)
            if total > 5:
                messages.append(f"{zone_type.capitalize()} {zone_price} has been broken by ${total}")
                buffer[zone_price] = []  # Reset buffer for that zone
        return messages
