from Feed import get_xauusd_4hr_candles

from support import AlertLogger,Reversal


class Trend:
    def __init__(self,server):
        self.reversal=Reversal()
        self.server=server
        self.log=AlertLogger(server.conn)
        self.sr=server.sr
        self.trend="Uknown"
    def start_signal(self, atr,direction):
        print("🔔 Starting trend analysis...")
        try:
            highs = self.sr.reversal_zones.get("highs", [])
            lows = self.sr.reversal_zones.get("lows", [])

            # Ensure enough data exists
            if len(highs) < 3 or len(lows) < 3:
                return False, False

            # Build zones dictionary
            zones = {
                "curr_high": highs[-1],
                "prev1_high": highs[-2],
                "prev2_high": highs[-3],
                "curr_low": lows[-1],
                "prev1_low": lows[-2],
                "prev2_low": lows[-3],
            }
            if zones :
                print(f"🔍 Analyzing zones and ATR={atr}:")
                for label, zone in zones.items():
                    ts = zone.get("timestamp", "⛔️ No timestamp")
                    price = zone.get("price", "⛔️ No price")
                    print(f"  • {label}: price={price}, timestamp={ts}")

            def safe_chain(keys):
                try:
                    timestamps = [zones[k]["timestamp"] for k in keys]
                    if not all(hasattr(t, 'timestamp') or hasattr(t, 'isoformat') or hasattr(t, 'year') for t in
                               timestamps):
                        return False
                    return all(timestamps[i] < timestamps[i + 1] for i in range(len(timestamps) - 1))
                except Exception as e:
                    print(f"unexpected error in safe_chain: {e}")
                    self.log.log(f"⚠️ *Error in safe_chain:* `{e}`")
                    return False

            # Define the sequences
            sec1_keys = ["curr_high", "curr_low"]
            sec2_keys = ["curr_low", "curr_high"]

            # Evaluate both sequences safely
            sec1 = safe_chain(sec1_keys)
            sec2 = safe_chain(sec2_keys)
            msg= self.classic_uptrend(zones, atr, sec1) or \
                 self.expansion_buy(zones, atr, sec1) or \
                 self.contraction(zones, atr, sec1) or \
                 self.ascending_triangle(zones, atr, sec1) or \
                 self.descending_midpoint(zones, atr, sec1) or \
                 self.classic_downtrend(zones, atr, sec2) or \
                 self.expansion_sell(zones, atr, sec2) or \
                 self.bull_ears(zones, atr, sec2) or \
                 self.v_lows(zones, atr, sec1) or \
                 self.ascending_m(zones, atr, sec1)
            if msg:
                if direction=="up" and self.sr.signal_flag==True:
                 self.log.log(f"🔔 buy*Trend Signal*: `{msg}`")
                 self.sr.signal_flag=False
                elif direction=="down" and self.sr.signal_flag==True:
                 self.log.log(f"🔔 sell*Trend Signal*: `{msg}`")
                 self.sr.signal_flag=False
                else :print(f"🔔 Trend detected: {msg}")
            else:
                print("🔍 No trend detected.")
            return False, False


        except Exception as e:
            print(f"unexpected error in start_signal:{e}")
            self.log.log(f"⚠️ *Error in start_signal*: `{e}`")
            return False, False

    def update_trend(self, new_trend):
        assert new_trend in {"uptrend", "downtrend", "ranging", "unknown"}, "Invalid trend value"
        self.trend = new_trend
        print(f"🔄 Trend updated to: {new_trend}")
    def init_trend(self):
        candles = get_xauusd_4hr_candles()
        if candles is None or len(candles) < 3:
            print("❌ Failed to fetch initial candles for trend determination.")
            return "unknown"

        try:
            highs = [candle['high'] for candle in candles]
            lows = [candle['low'] for candle in candles]

            if highs[2] > highs[1] > highs[0] and lows[2] > lows[1] > lows[0]:
                self.trend = "uptrend"
            elif highs[2] < highs[1] < highs[0] and lows[2] < lows[1] < lows[0]:
                self.trend = "downtrend"
            else:
                self.trend = "ranging"
            self.calculate_overlap_percentages(candles)
            print(f"✅ Initial trend determined: {self.trend}")
            return self.trend

        except Exception as e:
            print(f"⚠️ Error determining initial trend: {e}")
            return "unknown"

    def calculate_overlap_percentages(self, candles):
        if len(candles) < 3:
            raise ValueError("Need at least 3 candles to calculate overlaps.")

        def overlap_percentage(c1, c2):
            overlap_low = max(c1['low'], c2['low'])
            overlap_high = min(c1['high'], c2['high'])

            if overlap_low >= overlap_high:
                return 0.0

            overlap_size = overlap_high - overlap_low
            range1 = c1['high'] - c1['low']
            range2 = c2['high'] - c2['low']
            avg_range = (range1 + range2) / 2

            return round((overlap_size / avg_range) * 100, 2)

        latest = candles[-1]
        prev1 = candles[-2]
        prev2 = candles[-3]
        latest_prev1_overlap = overlap_percentage(latest, prev1)
        prev1_prev2_overlap = overlap_percentage(prev1, prev2)
        latest_prev2_overlap = overlap_percentage(latest, prev2)
        print(
            f"🔍 Overlap Percentages:\n"
            f"Latest vs Prev1 ➝ {latest_prev1_overlap:.2f}%\n"
            f"Prev1 vs Prev2 ➝ {prev1_prev2_overlap:.2f}%\n"
            f"Latest vs Prev2 ➝ {latest_prev2_overlap:.2f}%"
        )
        return {
            "latest_vs_prev1": latest_prev1_overlap,
            "prev1_vs_prev2": prev1_prev2_overlap,
            "latest_vs_prev2": latest_prev2_overlap
        }
    def classic_uptrend(self, zones, atr, sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            higher_high = curr_high > prev1_high
            higher_low = curr_low > prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if higher_high and higher_low and swing_size and sec1 :
                return "📈 Classic Uptrend detected: Higher Highs and Higher Lows"
            return False

        except KeyError:
            return False



    def expansion_sell(self,zones,atr,sec2):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            prev2_high = zones["prev2_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]

            higher_high = curr_high > prev1_high > prev2_high
            lower_low = curr_low <prev1_low
            swing_size = (curr_high - curr_low) >= atr
            if higher_high and lower_low and swing_size and sec2:
                return "📈 Sell Expansion trend detected: Higher Highs and Lower Lows"
            return False
        except KeyError:
            return False
    def expansion_buy(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            prev2_low = zones["prev2_low"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]

            higher_high = curr_high > prev1_high
            lower_low = curr_low > prev1_low and prev1_low <prev2_low
            swing_size = (curr_high - curr_low) >= atr
            if higher_high and lower_low and swing_size and sec1:
                return "📈 Buy Expansion trend detected: higher Highs and Higher Lows"
            return False
        except KeyError:
            return False

    def contraction(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            lower_high = curr_high < prev1_high
            higher_low = curr_low > prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if lower_high and higher_low and swing_size and sec1 :
                return "📉 Contraction trend detected: Lower Highs and Higher Lows"
            return False

        except KeyError:
            return False
    def ascending_triangle(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            equal_high = curr_high - prev1_high <=0.4 * atr
            higher_low = curr_low > prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.2 * atr
            if equal_high and higher_low and swing_size and sec1:
                return "🔺 Ascending Triangle detected: Flat Highs and Rising Lows"
            return False
        except KeyError:
            return False
    def descending_midpoint(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            prev2_low = zones["prev2_low"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]

            equal_high = curr_high - prev1_high <= 0.4 * atr
            lower_low = curr_low < prev1_low and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= atr
            if equal_high and lower_low and swing_size and sec1 :
                return "🔻 Descending Midpoint detected: Flat Highs and Falling Lows"
            return False
        except KeyError:
            return False


    def classic_downtrend(self, zones, atr, sec2):
        try:
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            prev2_high = zones["prev2_high"]["price"]

            lower_low = curr_low < prev1_low
            lower_high = curr_high < prev1_high < prev2_high
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if lower_low and lower_high and swing_size and sec2 :
                return "📉 Classic Downtrend detected: Lower Highs and Lower Lows"
            return False

        except KeyError:
            return False
    def bull_ears(self,zones,atr,sec2):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            prev2_high = zones["prev2_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]

            higher_high = curr_high < prev1_high  and prev1_high > prev2_high
            higher_low = (curr_low -prev1_low )<= atr
            swing_size = (curr_high - curr_low) >= 0.5 * atr
            if higher_high and higher_low and swing_size and sec2:
                return "🚩 sell Bull ears detected"
            return False
        except KeyError:
            return False
    def v_lows(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            lower_high = curr_high < prev1_high
            lower_low = prev1_low < curr_low < prev2_low and prev1_low < prev2_low
            swing_size = (curr_high - curr_low) >= atr

            if lower_high and lower_low and swing_size and sec1:
                return "📈 V-Lows detected possible buy: Sharp Reversal with lower Highs and Lower Lows"
            return False

        except KeyError:
            return False
    def ascending_m(self,zones,atr,sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            higher_high = curr_high > prev1_high
            higher_low = curr_low< prev1_low  and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.8 * atr
            if higher_high and higher_low and swing_size and sec1:
                return "🚩 buy Ascending M detected"
            return False
        except KeyError:
            return False