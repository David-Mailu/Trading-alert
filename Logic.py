from bdb import effective
from collections import deque
from datetime import datetime, timedelta
from numpy.ma.core import resize

from  support import Reversal, AlertLogger

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
                ats= stats["ats"]
                ats_short= stats["ats_short"]
                bk_index= stats["breakout_index"]
                ats_index= stats["ats_index"]
                atr_index= stats["atr_index"]
                volume_index= stats["volume_index"]
                avr_volume_index= stats["avr_volume_index"]
                avr_atr_index= stats["avr_atr_index"]
                avr_ats_index= stats["avr_ats_index"]
                dir_index=bk_index*volume_index*atr_index*ats_index
                strength_index= stats["strength_index"]
            else:
                print("No stats available yet.")
                atr=None
                atv=None
                ats=None
                ats_short=None
                bk_index=None
                ats_index=None
                atr_index=None
                volume_index=None
                avr_volume_index=None
                avr_atr_index=None
                avr_ats_index=None
                dir_index=None
                strength_index=None
            msg=self.false_break_aware(tick_volume,atr,ats_short)
            if msg:
                self.log.log(msg)
            msg=self.reversal.reversal(self.store_candle,direction,tick_volume,ats)
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
                base0_base_size=base0_size+base_size
                base_next1_size=base_size+next1_size
                effective_size=base0_size+base_size+next1_size
                same_dir_base0_next1=(base0_direction==next1_direction) and base0_direction is not None
                same_dir_base_next1=(baze_direction==next1_direction) and baze_direction is not None
                if (effective_size>=0.2*atr or base0_base_size>=0.4*atr or base_next1_size>=0.4*atr)  and (same_dir_base0_next1 or same_dir_base_next1):
                    base_direction = "up"
                elif (effective_size>=-0.2*atr or base0_base_size>=-0.4*atr or base_next1_size>=-0.4*atr) and (same_dir_base0_next1 or same_dir_base_next1):
                    base_direction = "down"
                else:
                    base_direction=self.prev_base_direction
                self.prev_base_direction=base_direction
                prev_base_direction = "up" if float(next1["close"]) > float(next1["open"]) else "down" if float(
                    next1["close"]) < float(next1["open"]) else base_direction
                m1= self.definite_reversal(next1, [next2, next3], base_direction, direction,tick_volume,atr,atv,size,ats,ats_short,strength_index,prev_base_direction)
                if m1: msgs.append(m1)
                m2= self.reversal.is_wick_reversal(next1, [next2, next3],base_direction,tick_volume,ats_short,prev_base_direction)
                if m2: msgs.append(m2)

                m3= self.reversal.is_pullback_reversal([next2, next3],
                      base_direction,tick_volume,ats_short ,prev_base_direction)
                if m3: msgs.append(m3)
                m4 = self.reversal.engulfing_reversal([next1, next2, next3],
                      base_direction,tick_volume,ats_short )
                if m4: msgs.append(m4)
                self.add_zone(next1, [next2, next3],
                     base_direction, direction,tick_volume,ats,ats_short,prev_base_direction)

                for msg in msgs:
                    self.log.log(msg)
            self.fill_empty_zone(price,direction)
            msg = self.check_break(price, size, direction,tick_volume,ats)
            if msg:
                self.log.log(msg)
            self.depopularize(atr)
            self.promote_zone(price,direction,ats)
            # ⚡ Volatility / Momentum Notifications
            if (abs(self.prev_size) + abs(size)) >2*atr and atr>=5 and direction == self.prev_dir:
                msg = f"⚡ High Volatility AVG volume index {avr_volume_index:.2f} vs AVG ATR index{avr_atr_index:.2f}! AVG ATS index {avr_ats_index:.2f} and tick_volume {tick_volume} with Size: ${self.prev_size + size:.2f} and current price: {price} ats:{round(ats,2)} vs atr: {round(atr,2)}"
                self.log.log(msg)
            else:
                similar = (
                        self.prev_size and abs(abs(size) - abs(self.prev_size)) < 0.5*atr
                        and direction == self.prev_dir
                )
                clustered = (
                        self.last_break and datetime.now() - self.last_break < timedelta(minutes=30)
                )

                if similar or clustered:
                    print("🚫 Skipping volatility alert due to similar candle or recent SR break.")

            # Update previous cycle state
            self.prev_dir, self.prev_size= direction, size
            return atr,direction
        except Exception as e:
          print(f"💥 Uncaught error in logic: {e}")
          self.log.log(f"⚠️ *logic error:* `{e}`")


    def __init__(self,server):
        self.support=[]
        self.resistance=[]
        self.resistance_liquidity=[]
        self.support_liquidity=[]
        self.volume_ind_list=deque(maxlen=3)
        self.atr_ind_list=deque(maxlen=3)
        self.ats_ind_list=deque(maxlen=3)
        self.prev_false_break =[]
        self.consolidation_break=[]
        self.prev_base_direction=None
        self.reversal_zones = {"lows":deque(maxlen=3), "highs":deque(maxlen=3)}
        self.server=server
        self.log = AlertLogger(server.conn)
        self.reversal=Reversal()
        self.reversal_buffer = []
        self.prev_dir, self.prev_size = None, 0.0
        self.last_break = None
        self.store_candle=[]
        self.signal_flag=False
        self.tolerance = 2.0  # Default tolerance for SR breaks
        self.bounces = {"support": [], "resistance": []}
        # Track break types (for internal insight, optional)
        self.breaks = {
            "support": {"doji": 0, "momentum": 0, "high_volatility": 0},
            "resistance": {"doji": 0, "momentum": 0, "high_volatility": 0}
        }

        # Buffer of break sizes per zone
        self.break_buffer_detailed = {
            "support": deque(maxlen=3),      # Format: {"timestamp": ..., "zone": ..., "type": ...}
            "resistance": deque(maxlen=3)   # Format: {"timestamp": ..., "zone": ..., "type": ...}
        }

    def init_zones(self):
        print("📌 Enter SR levels (up to 4 each):")
        for i in range(4):
            s = input(f"Support {i+1}: ").strip()
            if s: self.support_liquidity.append(float(s))
            r = input(f"Resistance {i+1}: ").strip()
            if r: self.resistance_liquidity.append(float(r))

    def init_reversal_zones(self):
        print("📌 Enter Reversal SR levels (up to 4 each):")
        self.reversal_zones = {"lows": [], "highs": []}

        # Define simulated timestamps (latest first)
        time_offsets = [3, 2.5, 2, 1.5, 1, 0.5]  # in hours
        now = datetime.now()
        offset_index = 0

        for i in range(3):
            l = input(f"Reversal Support {i + 1}: ").strip()
            if l:
                timestamp = now - timedelta(hours=time_offsets[offset_index])
                self.reversal_zones["lows"].append({
                    "price": float(l),
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
                offset_index += 1

            h = input(f"Reversal Resistance {i + 1}: ").strip()
            if h:
                timestamp = now - timedelta(hours=time_offsets[offset_index])
                self.reversal_zones["highs"].append({
                    "price": float(h),
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
                offset_index += 1

    def classify(self, size,ats):
        return "doji" if abs(size) < 0.5*ats else "momentum" if abs(size) <= 2.5*ats else "high_volatility"

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
        volume_list =[]
        size_list=[]
        tr_ts=[]

        for i in range(1, len(self.store_candle)):
            current = self.store_candle[i]
            previous = self.store_candle[i - 1]

            high = float(current['high'])
            low = float(current['low'])
            prev_close =float(previous['close'])
            volume = float(current['tick_volume'])
            open=float(current['open'])
            close=float(current['close'])

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            size=abs(close - open)
            size_list.append(size)
            tr_ts_ratio=tr/size if size!=0 else 0
            tr_ts.append(tr_ts_ratio)
            tr_list.append(tr)
            volume_list.append(volume)

        atr = float(sum(tr_list) / len(tr_list))
        atv = float(sum(volume_list) / len(volume_list))
        ats= float(sum(size_list) / len(size_list))
        atr_ats_ratio= atr/ats if ats!=0 else 0
        atr_ats= float(sum(tr_ts)/len(tr_ts)) if len(tr_ts)>0 else 0
        breakout_index=atr_ats/atr_ats_ratio if atr_ats_ratio!=0 else 0
        ats_short= float(sum(size_list[-5:]) / 5)  # Last 5 candles average size
        atr_short= float(sum(tr_list[-5:]) / 5) # Last 5 candles average tr
        volume_short= float(sum(volume_list[-5:]) / 5) # Last 5 candles average volume
        volume_index= volume_short/atv if atv!=0 else 0
        atr_index= atr_short/atr if atr!=0 else 0
        ats_index=ats_short/ats if ats!=0 else 0
        avg_volume=float(sum(volume_list[-3:])/3) if len(volume_list)>=3 else volume_short
        self.volume_ind_list.append(volume_index)
        self.atr_ind_list.append(atr_index)
        self.ats_ind_list.append(ats_index)
        if len(self.volume_ind_list)==3:
            avr_volume_index= float(sum(self.volume_ind_list)/len(self.volume_ind_list))
        else:
            avr_volume_index=volume_index
        if len(self.atr_ind_list)==3:
            avr_atr_index= float(sum(self.atr_ind_list)/len(self.atr_ind_list))
        else:
            avr_atr_index=atr_index
        if len(self.ats_ind_list)==3:
            avr_ats_index= float(sum(self.ats_ind_list)/len(self.ats_ind_list))
        else:
            avr_ats_index=ats_index
        commit_index=avr_ats_index*avr_atr_index*avr_volume_index
        strength=commit_index**(1/3)
        if avg_volume>1500 and strength<1:
            strength_index=1.0
        else:
            strength_index=strength
        print (f"📊 ATS_SHORT vs ATS: {ats_short:.2f} vs {ats:.2f} | ATR: {atr:.2f} | ATR/ATS ratio: {atr / ats:.2f} vs breakout index {breakout_index:.2f} vs  ATS index {ats_index:.2f} ATR index {atr_index:.2f} volume index {volume_index:.2f} volume/atv ratio: {volume/atv:.2f}")
        print(f"📊 3-candle Avg Volume Index: {avr_volume_index:.2f} |  Avg ATR Index: {avr_atr_index:.2f}  Avg ATS Index: {avr_ats_index:.2f} | Commitment Index: {commit_index:.2f} | Strength Index: {strength_index:.2f}")
        return {
            "atr": atr,
            "atv": atv,
            "ats": ats,
            "ats_short": ats_short,
            "breakout_index": breakout_index,
            "ats_index": ats_index,
            "atr_index": atr_index,
            "volume_index": volume_index,
            "avr_volume_index": avr_volume_index,
            "avr_atr_index": avr_atr_index,
            "avr_ats_index": avr_ats_index,
            "strength_index": strength_index
        }
    def get_nearest_zone(self, zone_type, price):
        zones = self.support if zone_type == "support" else self.resistance
        if not zones:
            print (f"🚫 No: {zones} defined.")
            return None
        nearest = min(zones, key=lambda z: abs(z - price))
        return nearest

    def check_break(self, price, size, direction,tick_volume,ats):
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
        break_size= abs(price - zone_price)
        threshold= ats if ats<5 else 5

        broken = (
            price < zone_price - threshold if zone_type == "support"
            else price > zone_price + threshold
        )

        if broken and effective_size > 0.9*threshold:
            category = self.classify(effective_size,ats)
            self.breaks[zone_type][category] += 1
            self.break_buffer_detailed[label].append({"timestamp": ts, "zone": zone_price, "type": category, "price": price, "size": round(effective_size,2), "tick_volume": tick_volume})
            return f"🚨 {zone_type.capitalize()} break at {zone_price} Broken! by Price: {price},  Size: ${round(break_size,2)}, Type: {category} and tick_volume: {tick_volume}"

        elif not broken:
            print(f"no break detected  price: {price} not beyond zone: {zone_price} with tolerance: {threshold:.2f}")
            return None

    def promote_zone(self,current_price,direction,ats):
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
        threshold = ats * self.tolerance
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

    def get_extreme_zone(self,candles, direction):
        if direction == "up":
            return min(float(c["low"]) for c in candles)
        elif direction == "down":
            return max(float(c["high"]) for c in candles)
        return None


    def add_zone(self, next1, next_two, base_direction, direction, tick_volume,ats,ats_short,prev_base_direction):
        if direction not in ["up", "down"]:
            return None

        next2,next3= next_two  # Assuming next_two = [next2, next3]
        zone_candidates=[next1,next2,next3]

        # Define reversal checks
        reversal_checks = [
            ("wick", self.reversal.is_wick_reversal(next1, next_two, base_direction, tick_volume,ats_short,prev_base_direction), next1),
            ("pullback", self.reversal.is_pullback_reversal(next_two, base_direction, tick_volume,ats_short,prev_base_direction), next1),
            ("engulf", self.reversal.engulfing_reversal([next1] + next_two, base_direction, tick_volume,ats_short), next3),
            ("buffer", self.reversal.reversal(self.reversal_buffer, direction, tick_volume,ats), next1)
        ]

        for label, triggered, zone_candle in reversal_checks:
            if triggered:
                new_zone = self.get_extreme_zone(zone_candidates, direction)

                # Update support/resistance
                target_list = self.support if direction == "up" else self.resistance
                opposite_list = self.resistance if direction == "up" else self.support

                if new_zone not in target_list:
                    target_list.append(new_zone)
                if new_zone in opposite_list:
                    opposite_list.remove(new_zone)

                return None  # Exit after first valid reversal

        return None

    def is_clustered_zone_recent(self, label, window_minutes=45.5):
        """
        Checks if a reversal zone of the given label ('lows' or 'highs') was logged within the last window_minutes.
        Returns True if a recent zone exists, False otherwise.
        """
        now = datetime.now()
        recent_zones = self.reversal_zones.get(label, [])

        for zone in recent_zones:
            try:
                zone_time = datetime.fromisoformat(zone["timestamp"])
                if now - zone_time < timedelta(minutes=window_minutes):
                    return True
            except Exception as e:
                # Optional: log or handle malformed timestamp
                continue

        return False
    def definite_reversal(self, next1, next_two, base_direction, direction, tick_volume, atr, atv, size, ats,
                          ats_short,strength_index,prev_base_direction):
        """
        Combines all reversal types and logs confirmed reversal zones.
        Returns 'reversal_up' or 'reversal_down' if any reversal is confirmed.
        """
        if direction not in ["up", "down"]:
            return None

        next2, next3 = next_two  # Unpack for clarity
        zone_candidates = [next1, next2, next3]
        price= float(next3["close"])
        # Check reversal triggers
        wick = self.reversal.is_wick_reversal(next1, next_two, base_direction, tick_volume,ats_short,prev_base_direction)
        pullback = self.reversal.is_pullback_reversal(next_two, base_direction, tick_volume,ats_short,prev_base_direction)
        engulf = self.reversal.engulfing_reversal(zone_candidates, base_direction, tick_volume, ats_short)
        buffer = self.reversal.reversal(self.reversal_buffer, direction, tick_volume, ats)
        breakout=self.false_break_aware(tick_volume,atr,ats_short)
        # Determine zone price from extreme candle
        zone_price = self.get_extreme_zone(zone_candidates, direction)
        label = "lows" if direction == "up" else "highs"
        now=datetime.now()
        zone_clustered_recent=self.is_clustered_zone_recent(label) if now-self.server.recent_init>timedelta(minutes=45) else False
        # If any reversal confirmed
        if (wick or pullback or engulf or buffer or breakout) and not zone_clustered_recent:
            self.signal_flag=True
            timestamp = datetime.now().isoformat()
            volume_ratio = tick_volume / atv
            size_ratio = size / ats
            atr_ats_ratio = atr / ats

            if label not in self.reversal_zones:
                self.reversal_zones[label] = []
            self.reversal_zones[label].append({
                "price": zone_price,
                "timestamp": timestamp,
                "volume_ratio": volume_ratio,
                "size_ratio": size_ratio,
                "atr_ats_ratio": atr_ats_ratio,
                "tick_volume": tick_volume,
                "size": size,
                "atr": atr,
                "type": self.get_reversal_type(wick, pullback, engulf, buffer,breakout)
            })

            return f"reversal_{direction} and tick_volume: {round(tick_volume,2)} vs atv: {round(atv,2)} and size: {size:.2f} vs ats: {ats:.2f} vs atr: {atr:.2f} and price: {price}, strength indx: {strength_index:.2f}, size_ratio: {size_ratio:.2f}, atr_ats_ratio: {atr_ats_ratio:.2f}"

        return None


    def get_reversal_type(self, wick, pullback, engulf, buffer,breakout):
        if engulf:
            return "engulfing"
        elif wick:
            return "wick"
        elif pullback:
            return "pullback"
        elif buffer:
            return "buffer"
        elif wick and pullback:
            return "wick_pullback"
        elif breakout:
            return "false_break"
        return "unknown"

    def depopularize(self,atr):
        def filter_oldest(zones):
            kept = []
            for price, zone in enumerate(zones):
                # Check if val is close to any previously kept value
                if all(abs(zone - prev) > atr for prev in kept):
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
                new_zone = float((int(price) // 10) * 10)
                self.support.append(new_zone)
        return None
    def false_break_aware(self,tick_volume,atr,ats_short):
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

        if net_move < ats_short*1.2 <= recent_size <= 0.9*atr:

            self.prev_false_break.append({
                "timestamp": ts,
                "up": 1 if direction == "up" else 0,
                "down": 1 if direction == "down" else 0
            })

            return f"⚠️ Possible {direction} false break  recent size: {recent_size:.2f} vs atr:{atr:.2f} and tick_volume: {tick_volume}"
        if net_move<=ats_short*1.2 and recent_size>0.9*atr:

            self.consolidation_break.append({
                "timestamp": ts,
                "up": 1 if direction == "up" else 0,
                "down": 1 if direction == "down" else 0
            })
            return f"⚠️ Possible {direction} consolidation break  recent size: {recent_size:.2f} vs atr:{atr:.2f} and tick_volume: {tick_volume}"
        return None
    def candle_pattern(self):
        if len(self.store_candle)<3:
            return None
        base,next1,next2=self.store_candle[-3:]
        base_type=self.reversal.candle_body_type(base)
        next1_type=self.reversal.candle_body_type(next1)
        next2_type=self.reversal.candle_body_type(next2)
        if base_type=="maruboza" and next1_type=="doji" and next2_type=="maruboza":
            return "morning_star" if float(base["close"])<float(next2["close"]) else "evening_star"
        if next1_type=="maruboza" and next2_type=="maruboza":
            if self.reversal.is_down(base) and self.reversal.is_down(next1) and self.reversal.is_up(next2) and self.reversal.size(next)>self.reversal.size(next1):
                return "bearish_engulfing"
            if self.reversal.is_up(base) and self.reversal.is_up(next1) and self.reversal.is_down(next2) and self.reversal.size(next2)>self.reversal.size(next1):
                return "bullish_engulfing"
            if self.reversal.is_down(next1) and self.reversal.is_up(next2) and self.reversal.size(next1)>self.reversal.size(next2):
                return "bullish_pregnant"
            if self.reversal.is_up(next1) and self.reversal.is_down(next2) and self.reversal.size(next2)>self.reversal.size(next1):
                return "bearish_pregnant"
        if base_type=="maruboza" and next1_type==("hammer","shooting_star") and next2_type=="maruboza":
            if self.reversal.is_up(base) and self.reversal.is_down(next2) and next1_type=="shooting_star":
                return "upper_rejection"
            if self.reversal.is_down(base) and self.reversal.is_up(next2) and next1_type=="hammer":
                return "lower_rejection"
        return None