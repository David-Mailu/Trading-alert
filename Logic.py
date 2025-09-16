from bdb import effective
from collections import deque
from datetime import datetime, timedelta

from numpy.ma.core import resize

from  support import AlertLogger
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

    def is_downward_reversal(self, candle, next_two,base_direction):
        upper, lower = self.get_wicks(candle)
        if upper and lower is None:
            print("🚫 Invalid candle data for downward reversal check.")
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two]

        if upper > lower  and all(directions) and base_direction=="up" and any(s >= 2 for s in sizes):
            high = float(candle["high"])
            close_last = float(next_two[-1]["close"])
            size = round(high - close_last, 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔻 Downward Reversal (wick) at {ts}, size: ${size}"
        return None

    def is_upward_reversal(self, candle, next_two,base_direction):
        upper, lower = self.get_wicks(candle)
        if upper and lower is None:
            print("🚫 Invalid candle data for upward reversal check.")
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) > float(c["open"]) for c in next_two]

        if lower >upper and all(directions) and base_direction=="down" and any(s >= 2 for s in sizes):
            close_curr = float(next_two[-1]["close"])
            lows = [float(c["low"]) for c in next_two]
            size = round(close_curr - min(lows), 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔺 Upward Reversal (wick) at {ts}, size: ${size}"
        return None

    def is_pullback_reversal(self, next_two,base_direction):
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two] if base_direction == "up" else \
                     [float(c["close"]) > float(c["open"]) for c in next_two]

        if all(directions) and any(s >= 1.4 for s in sizes):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            if base_direction == "up":
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

    def engulfing_reversal(self, last_three, base_direction):
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
            if size_c3 > size_c2 and size_c3 >= 4:
                return f"🔻 Bearish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)}"

        # 🔺 Bullish Engulfing Reversal
        if base_direction == "down" and is_down(c1) and is_down(c2) and is_up(c3):
            if size_c3 > size_c2 and size_c3 >= 4:
                return f"🔺 Bullish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)}"

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
            if self.consolidation_count >=3 and not self.consolidation_triggered:
                self.consolidation_triggered = True
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                return f"⏸️ consolidation detected at {ts}, range: ${round(net_move, 2)}"
        else:
            self.consolidation_count = 0
            self.consolidation_triggered=False
        return None


class SRManager:
    def start_logic(self,candle):
        try:
            open_, close = float(candle["open"]), float(candle["close"])
            size = (close - open_)
            price = close
            direction = "up" if close > open_ else "down"
            color = "white" if direction is None else "green" if direction == "up" else "red"
            # 🧠 Reversal logic
            if direction =="up":
                self.green_candles.append(size)
            elif direction =="down":
                self.red_candles.append(size)
            else:
                print(f"doji: {color} and size {size}")
                return None
            self.store_candle(size)
            self.reversal_buffer.append(candle)
            if len(self.reversal_buffer) > 4:
                self.reversal_buffer.pop(0)

            if len(self.reversal_buffer) == 4:
                base, next1, next2,next3 = self.reversal_buffer
                msgs = []
                base_size = (float(base["close"]) - float(base["open"]))
                baze_direction = "up" if float(base["close"]) > float(base["open"]) else "down" if float(base["close"]) < float(base["open"]) else None
                next1_size = (float(next1["close"]) - float(next1["open"]))
                next1_direction = "up" if float(next1["close"]) > float(next1["open"]) else "down" if float(next1["close"]) < float(next1["open"]) else None
                effective_size=base_size+next1_size
                if effective_size>=2 and baze_direction=="up" and next1_direction=="up":
                    base_direction = "up"
                elif effective_size<=-2 and baze_direction=="down" and next1_direction=="down":
                    base_direction = "down"
                else:
                    base_direction=None

                m1 = self.reversal.is_downward_reversal(next1, [next2, next3],base_direction)
                if m1: msgs.append(m1)

                m2 = self.reversal.is_upward_reversal(next1, [next2, next3],base_direction)
                if m2: msgs.append(m2)

                m3 = self.reversal.is_pullback_reversal([next2, next3],
                      base_direction )
                if m3: msgs.append(m3)
                m4 = self.reversal.engulfing_reversal([next1, next2, next3],
                      base_direction )
                if m4: msgs.append(m4)
                self.add_zone(next1, [next2, next3],
                     base_direction, direction)

                for msg in msgs:
                    self.log.log(msg)

                msg = self.reversal.detect_consolidation(self.reversal_buffer)
                if msg:
                    self.log.log(msg)

            msg = self.check_break(price, size, direction)
            if msg:
                self.log.log(msg)
            self.depopularize()
            self.promote_zone(price,direction)
            # ⚡ Volatility / Momentum Notifications
            if (abs(self.prev_size) + abs(size)) > 10 and direction == self.prev_dir:
                msg = f"⚡ High Volatility! Size: ${self.prev_size + size} and current price: {price}"
                self.log.log(msg)
            else:
                similar = (
                        self.prev_size and abs(abs(size) - abs(self.prev_size)) < 0.5
                        and direction == self.prev_dir
                )
                clustered = (
                        self.last_break and datetime.now() - self.last_break < timedelta(minutes=30)
                )

                if similar or clustered:
                    print("🚫 Skipping volatility alert due to similar candle or recent SR break.")

            # Update previous cycle state
            self.prev_dir, self.prev_size, self.last_color = direction, size, color
        except Exception as e:
          print(f"💥 Uncaught error in logic: {e}")
          self.log.log(f"⚠️ *logic error:* `{e}`")


    def get_status_payload(self):
        status ="🟢 active" if self.server.paused==False else "🔴 paused"

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
        self.support=[]
        self.resistance=[]
        self.last_color=None
        self.red_candles, self.green_candles = [], []
        self.server=server
        self.log = AlertLogger(server.conn)
        self.reversal=Reversal()
        self.reversal_buffer = []
        self.prev_dir, self.prev_size = None, 0.0
        self.last_break = None
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
            print (f"🚫 No: {zones} defined.")
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
            return f"🚨 {zone_type.capitalize()} break at {zone_price} Broken! by Price: {price},  Size: ${round(effective_size,2)}, Type: {category}"

        elif not broken:
            print("no break detected")
            return None

    def promote_zone(self,current_price,direction,threshold=6):
        if direction == "up":
            zone_type = "resistance"
        elif direction == "down":
            zone_type = "support"
        else:
            print("🚫 Invalid direction for zone promotion.")
            return None
        zone_list= self.support if zone_type == "support" else self.resistance
        if not zone_list:
            print("🚫 No zones found.")
            return None

        for price in zone_list:
            if zone_type == 'resistance' and current_price >= price + threshold:
                if price not in self.support:
                    self.support.append(price)
                if price in self.resistance:
                    self.resistance.remove(price)

            elif zone_type == 'support' and current_price <= price - threshold:
                if price not in self.resistance:
                    self.resistance.append(price)
                if price in self.support:
                    self.support.remove(price)

    def add_zone(self, next1, next_two, base_direction, direction):
        new_zone = float(next1["high"]) if direction == "down" else float(next1["low"])
        if self.reversal.is_upward_reversal(next1, next_two,base_direction) and direction == "up":
            if new_zone not in self.support:
                self.support.append(new_zone)
            if new_zone in self.resistance:
                self.resistance.remove(new_zone)
        elif self.reversal.is_downward_reversal(next1, next_two,base_direction) and direction == "down":
            if new_zone not in self.resistance:
                self.resistance.append(new_zone)
            if new_zone in self.support:
                self.support.remove(new_zone)
        elif self.reversal.is_pullback_reversal(next_two, base_direction) and direction in ["up", "down"]:
            if direction == "up":
                if new_zone not in self.support:
                    self.support.append(new_zone)
                if new_zone in self.resistance:
                    self.resistance.remove(new_zone)
            else:
                if new_zone not in self.resistance:
                    self.resistance.append(new_zone)
                if new_zone in self.support:
                    self.support.remove(new_zone)
        else:
            return None

    def depopularize(self, threshold=2.0):
        def filter_oldest(zones):
            kept = []
            for price, zone in enumerate(zones):
                # Check if val is close to any previously kept value
                if all(abs(zone - prev) > threshold for prev in kept):
                    kept.append(zone)
            return kept

        self.support = filter_oldest(self.support)
        self.resistance = filter_oldest(self.resistance)