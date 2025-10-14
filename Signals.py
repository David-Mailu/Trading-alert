import socket
import traceback
from ctypes.wintypes import SMALL_RECT

from Logic import SRManager, Reversal
from datetime import datetime

from support import AlertLogger


class Trend:
    def __init__(self,server):
        self.reversal=Reversal()
        self.server=server
        self.log=AlertLogger(server.conn)
        self.sr=server.sr
    def start_signal(self, atr):
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
                print("🔍 Constructed Zones:")
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
            sec1_keys = ["prev2_low", "prev1_high", "prev1_low", "curr_high", "curr_low"]
            sec2_keys = ["prev2_high", "prev1_low", "prev1_high", "curr_low", "curr_high"]

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
                self.log.log(f"🔔 *Trend Signal*: `{msg}`")
            else:
                print("🔍 No trend detected.")
            return False, False


        except Exception as e:
            print(f"unexpected error in start_signal:{e}")
            self.log.log(f"⚠️ *Error in start_signal*: `{e}`")
            return False, False


    def classic_uptrend(self, zones, atr, sec1):
        try:
            curr_high = zones["curr_high"]["price"]
            prev1_high = zones["prev1_high"]["price"]
            curr_low = zones["curr_low"]["price"]
            prev1_low = zones["prev1_low"]["price"]
            prev2_low = zones["prev2_low"]["price"]

            higher_high = curr_high > prev1_high + 0.1 * atr
            higher_low = curr_low > prev1_low + 0.1 * atr and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if higher_high and higher_low and swing_size and sec1:
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

            higher_high = curr_high > prev1_high + 0.1 * atr and prev1_high > prev2_high
            lower_low = curr_low <prev1_low + 0.1 * atr
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

            higher_high = curr_high > prev1_high + 0.1 * atr
            lower_low = curr_low > prev1_low + 0.1 * atr and prev1_low <prev2_low
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

            lower_high = curr_high < prev1_high - 0.1 * atr
            higher_low = curr_low > prev1_low + 0.1 * atr and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if lower_high and higher_low and swing_size and sec1:
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
            higher_low = curr_low > prev1_low + 0.1 * atr and prev1_low > prev2_low
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
            lower_low = curr_low < prev1_low + 0.1 * atr and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= atr
            if equal_high and lower_low and swing_size and sec1:
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

            lower_low = curr_low < prev1_low - 0.1 * atr
            lower_high = curr_high < prev1_high - 0.1 * atr and prev1_high < prev2_high
            swing_size = (curr_high - curr_low) >= 0.5 * atr

            if lower_low and lower_high and swing_size and sec2:
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

            higher_high = curr_high < prev1_high + 0.3 * atr and prev1_high > prev2_high
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

            lower_high = curr_high < prev1_high + 0.1* atr
            lower_low = prev1_low - 0.2 * atr < curr_low < prev2_low and prev1_low < prev2_low
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

            higher_high = curr_high > prev1_high + 0.1 * atr
            higher_low = curr_low< prev1_low + 0.1 * atr and prev1_low > prev2_low
            swing_size = (curr_high - curr_low) >= 0.8 * atr
            if higher_high and higher_low and swing_size and sec1:
                return "🚩 buy Ascending M detected"
            return False
        except KeyError:
            return False