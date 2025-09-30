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


    def is_wick_reversal(self, candle, next_two,base_direction,tick_volume):
        upper, lower = self.get_wicks(candle)
        if upper and lower is None:
            print("🚫 Invalid candle data for upward reversal check.")
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions_up = [float(c["close"]) > float(c["open"]) for c in next_two]
        direction_down = [float(c["close"]) < float(c["open"]) for c in next_two]

        if lower >upper and all(directions_up) and base_direction=="down" and any(s >= 2 for s in sizes):
            close_curr = float(next_two[-1]["close"])
            lows = [float(c["low"]) for c in next_two]
            size = round(close_curr - min(lows), 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔺 Upward Reversal (wick) at {ts}, size: ${size} and tick_volume: {tick_volume}"
        if upper > lower and all(direction_down) and base_direction == "up" and any(s >= 2 for s in sizes):
            high = float(candle["high"])
            close_last = float(next_two[-1]["close"])
            size = round(high - close_last, 2)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"🔻 Downward Reversal (wick) at {ts}, size: ${size} and tick_volume: {tick_volume}"
        return None

    def is_pullback_reversal(self, next_two,base_direction,tick_volume):
        if base_direction not in ["up", "down"]:
            return None
        sizes = [abs(float(c["close"]) - float(c["open"])) for c in next_two]
        directions = [float(c["close"]) < float(c["open"]) for c in next_two] if base_direction == "up" else \
                     [float(c["close"]) > float(c["open"]) for c in next_two]

        if all(directions) and any(s >= 1 for s in sizes):
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

    def engulfing_reversal(self, last_three, base_direction,tick_volume):
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
            if size_c3 > (size_c2+2) and size_c3 >= 4:
                return f"🔻 Bearish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)} and tick_volume: {tick_volume}"

        # 🔺 Bullish Engulfing Reversal
        if base_direction == "down" and is_down(c1) and is_down(c2) and is_up(c3):
            if size_c3 > (size_c2+2) and size_c3 >= 4:
                return f"🔺 Bullish Engulfing Reversal at {ts}, size: ${round(size_c3, 2)} and tick_volume: {tick_volume}"

        return None

    def reversal(self, store_candle, recent_direction, tick_volume):
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
                directions[0] == "down" and sizes[0] >= 0.5 and
                directions[1] == "down" and sizes[1] >= 0.5 and
                directions[2] == "up" and sizes[2] >= 4 and
                directions[3] == "down" and sizes[3] >= 0.1 and
                directions[4] == "down" and sizes[4] >= 0.5
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


class SRManager:
    def start_logic(self,candle):
        try:
            open_, close,tick_volume = float(candle["open"]), float(candle["close"]),float(candle["tick_volume"])
            size = (close - open_)
            price = close
            direction = "up" if close > open_ else "down"
            self.store_candle.append(candle)
            if len(self.store_candle)>14:
                self.store_candle.pop(0)
            stats= self.get_candle_stats()
            if stats:
                atr= stats["atr"]
                atv= stats["atv"]
            else:
                print("No stats available yet.")
                atr=None
                atv=None
            msg=self.false_break_aware(tick_volume,atr)
            if msg:
                self.log.log(msg)
            msg=self.reversal.reversal(self.store_candle,direction,tick_volume)
            if msg:
                self.log.log(msg)
            self.reversal_buffer.append(candle)
            if len(self.reversal_buffer) > 5:
                self.reversal_buffer.pop(0)

            if len(self.reversal_buffer) == 5:
                base0,base, next1, next2,next3 = self.reversal_buffer
                msgs = []
                size=abs(float(next3["close"])-float(next3["open"]))
                base0_size = (float(base0["close"]) - float(base0["open"]))
                base0_direction = "up" if float(base0["close"]) > float(base0["open"]) else "down" if float(base0["close"]) < float(base0["open"]) else None
                base_size = (float(base["close"]) - float(base["open"]))
                baze_direction = "up" if float(base["close"]) > float(base["open"]) else "down" if float(base["close"]) < float(base["open"]) else None
                next1_size = (float(next1["close"]) - float(next1["open"]))
                next1_direction = "up" if float(next1["close"]) > float(next1["open"]) else "down" if float(next1["close"]) < float(next1["open"]) else None
                effective_size=base0_size+base_size+next1_size
                same_dir_base0_next1=(base0_direction==next1_direction) and base0_direction is not None
                same_dir_base_next1=(baze_direction==next1_direction) and baze_direction is not None
                if effective_size>=0.1  and (same_dir_base0_next1 or same_dir_base_next1):
                    base_direction = "up"
                elif effective_size<=-0.1 and (same_dir_base0_next1 or same_dir_base_next1):
                    base_direction = "down"
                else:
                    base_direction=self.prev_base_direction
                self.prev_base_direction=base_direction
                m1= self.definite_reversal(next1, [next2, next3], base_direction, direction,tick_volume,atr,atv,size)
                if m1: msgs.append(m1)
                m2= self.reversal.is_wick_reversal(next1, [next2, next3],base_direction,tick_volume)
                if m2: msgs.append(m2)

                m3= self.reversal.is_pullback_reversal([next2, next3],
                      base_direction,tick_volume )
                if m3: msgs.append(m3)
                m4 = self.reversal.engulfing_reversal([next1, next2, next3],
                      base_direction,tick_volume )
                if m4: msgs.append(m4)
                self.add_zone(next1, [next2, next3],
                     base_direction, direction,tick_volume)

                for msg in msgs:
                    self.log.log(msg)
            self.fill_empty_zone(price,direction)
            msg = self.check_break(price, size, direction,tick_volume)
            if msg:
                self.log.log(msg)
            self.depopularize()
            self.promote_zone(price,direction)
            # ⚡ Volatility / Momentum Notifications
            if (abs(self.prev_size) + abs(size)) > 10 and direction == self.prev_dir:
                msg = f"⚡ High Volatility! and tick_volume {tick_volume} with Size: ${self.prev_size + size} and current price: {price} vs atr: {round(atr,2) if atr else 'N/A'}"
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
            self.prev_dir, self.prev_size= direction, size
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
        self.prev_false_break =[]
        self.consolidation_break=[]
        self.prev_base_direction=None
        self.reversal_zones = {"lows": [], "highs": []}
        self.server=server
        self.log = AlertLogger(server.conn)
        self.reversal=Reversal()
        self.reversal_buffer = []
        self.prev_dir, self.prev_size = None, 0.0
        self.last_break = None
        self.store_candle=[]
        self.tolerance = 2.0  # Default tolerance for SR breaks
        self.bounces = {"support": [], "resistance": []}
        # Track break types (for internal insight, optional)
        self.breaks = {
            "support": {"doji": 0, "momentum": 0, "high_volatility": 0},
            "resistance": {"doji": 0, "momentum": 0, "high_volatility": 0}
        }

        # Buffer of break sizes per zone
        self.break_buffer_detailed = {
            "support": [],      # Format: {"timestamp": ..., "zone": ..., "type": ...}
            "resistance": []
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

    def get_candle_stats(self):
        """
        Returns a dictionary with ATR and ATV calculated from self.store_candle.
        Requires at least 5 candles.
        Each candle must have 'high', 'low', 'close', and 'tick_volume'.
        """
        if len(self.store_candle) < 5:
            print("⚠️ Not enough candles to calculate stats (need ≥ 5).")
            return None

        tr_list = []
        volume_list = []

        for i in range(1, len(self.store_candle)):
            current = self.store_candle[i]
            previous = self.store_candle[i - 1]

            high = current['high']
            low = current['low']
            prev_close = previous['close']
            volume = current['tick_volume']

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
            volume_list.append(volume)

        atr = float(sum(tr_list) / len(tr_list))
        atv = float(sum(volume_list) / len(volume_list))

        return {
            "atr": atr,
            "atv": atv
        }
    def get_nearest_zone(self, zone_type, price):
        zones = self.support if zone_type == "support" else self.resistance
        if not zones:
            print (f"🚫 No: {zones} defined.")
            return None
        nearest = min(zones, key=lambda z: abs(z - price))
        return nearest

    def check_break(self, price, size, direction,tick_volume):
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
        label="support" if zone_type=="support" else "resistance"
        ts= datetime.now().strftime("%Y-%m-%d %H:%M")

        broken = (
            price < zone_price - self.tolerance if zone_type == "support"
            else price > zone_price + self.tolerance
        )

        if broken and effective_size > 1:
            category = self.classify(effective_size)
            self.breaks[zone_type][category] += 1
            self.break_buffer_detailed[label].append({"timestamp": ts, "zone": zone_price, "type": category, "price": price, "size": round(effective_size,2), "tick_volume": tick_volume})
            return f"🚨 {zone_type.capitalize()} break at {zone_price} Broken! by Price: {price},  Size: ${round(effective_size,2)}, Type: {category} and tick_volume: {tick_volume}"

        elif not broken:
            print(f"no break detected  price: {price} not beyond zone: {zone_price} with tolerance: {self.tolerance}")
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

    def add_zone(self, next1, next_two, base_direction, direction, tick_volume):
        if direction not in ["up", "down"]:
            return None

        # Define reversal checks
        reversal_checks = [
            ("wick", self.reversal.is_wick_reversal(next1, next_two, base_direction, tick_volume), next1),
            ("pullback", self.reversal.is_pullback_reversal(next_two, base_direction, tick_volume), next1),
            ("engulf", self.reversal.engulfing_reversal([next1] + next_two, base_direction, tick_volume), next_two[-1]),
            ("buffer", self.reversal.reversal(self.reversal_buffer, direction, tick_volume), next1)
        ]

        for label, triggered, zone_candle in reversal_checks:
            if triggered:
                new_zone = float(zone_candle["high"]) if direction == "down" else float(zone_candle["low"])

                # Update support/resistance
                target_list = self.support if direction == "up" else self.resistance
                opposite_list = self.resistance if direction == "up" else self.support

                if new_zone not in target_list:
                    target_list.append(new_zone)
                if new_zone in opposite_list:
                    opposite_list.remove(new_zone)

                return  None # Exit after first valid reversal

        return None


    def definite_reversal(self, next1, next_two, base_direction, direction, tick_volume,atr,atv,size):
        """
        Combines all reversal types and logs confirmed reversal zones.
        Returns 'reversal_up' or 'reversal_down' if any reversal is confirmed.
        """
        if direction not in ["up", "down"]:
            return None

        # Check reversal triggers
        wick = self.reversal.is_wick_reversal(next1, next_two, base_direction, tick_volume)
        pullback = self.reversal.is_pullback_reversal(next_two, base_direction, tick_volume)
        engulf = self.reversal.engulfing_reversal([next1] + next_two, base_direction, tick_volume)
        buffer = self.reversal.reversal(self.reversal_buffer, direction, tick_volume)

        # Determine zone price
        if engulf:
            next2 = next_two[-1]
            zone_price = float(next2["low"]) if direction == "up" else float(next2["high"])
        else:
            zone_price = float(next1["low"]) if direction == "up" else float(next1["high"])

        # If any reversal confirmed
        if wick or pullback or engulf or buffer:
            label = "lows" if direction == "up" else "highs"
            timestamp = datetime.now().isoformat()

            if label not in self.reversal_zones:
                self.reversal_zones[label] = []

            self.reversal_zones[label].append({
                "price": zone_price,
                "timestamp": timestamp,
                "tick_volume": tick_volume,
                "atv": atv,
                "size": size,
                "atr": atr,
                "type": self.get_reversal_type(wick, pullback, engulf, buffer)
            })

            return f"reversal_{label} and tick_volume: {tick_volume} vs atv: {atv} and size: {size} vs atr: {atr}"

        return None

    def get_reversal_type(self, wick, pullback, engulf, buffer):
        if engulf:
            return "engulfing"
        elif wick:
            return "wick"
        elif pullback:
            return "pullback"
        elif buffer:
            return "buffer"
        return "unknown"

    def depopularize(self,threshold=3.0):
        def filter_oldest(zones):
            kept = []
            for price, zone in enumerate(zones):
                # Check if val is close to any previously kept value
                if all(abs(zone - prev) > threshold for prev in kept):
                    kept.append(zone)
            return kept

        self.support = filter_oldest(self.support)
        self.resistance = filter_oldest(self.resistance)
    def fill_empty_zone(self,price,direction):
        if direction == "up":
            if not self.resistance:
                new_zone = float(((int(price) // 10) + 1) * 10)
                self.resistance.append(new_zone)
        if direction == "down":
            if not self.support:
                new_zone = float(((int(price) // 10)) * 10)
                self.support.append(new_zone)
        return None
    def false_break_aware(self,tick_volume,atr):
        if len(self.store_candle) < 5:
            print("🚫 Not enough candles to evaluate false break.")
            return None

        recent_five = self.store_candle[-5:]
        last_four = recent_five[:-1]
        recent_candle = recent_five[-1]

        try:
            open_first = last_four[0]["open"]
            close_last = last_four[-1]["close"]
            recent_open = recent_candle["open"]
            recent_close = recent_candle["close"]
        except (KeyError, TypeError):
            print("🚫 Invalid candle structure.")
            return None

        net_move = abs(close_last - open_first)
        recent_size = abs(recent_close - recent_open)
        direction="up" if recent_close>recent_open else "down"
        ts=datetime.now().strftime("%Y-%m-%d %H:%M")
        label="lows" if recent_close>recent_open else "highs"
        zone_price= float(recent_candle["low"]) if direction=="up" else float(recent_candle["high"])

        if net_move < 1.5 and 2<=recent_size <= 4 :
            self.reversal_zones[label].append({
                "price": zone_price,
                "timestamp": ts
            })
            self.prev_false_break.append({
                "timestamp": ts,
                "up": 1 if direction == "up" else 0,
                "down": 1 if direction == "down" else 0
            })

            return f"⚠️ Possible {direction} false break at {ts}, recent size: {recent_size} vs atr:{atr} and tick_volume: {tick_volume}"
        if net_move<=1.5 and recent_size>4:

            self.consolidation_break.append({
                "timestamp": ts,
                "up": 1 if direction == "up" else 0,
                "down": 1 if direction == "down" else 0
            })
            return f"⚠️ Possible {direction} consolidation break at {ts}, recent size: {recent_size} vs atr:{atr} and tick_volume: {tick_volume}"
        return None
