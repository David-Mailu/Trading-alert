import MetaTrader5 as mt5
from datetime import datetime
import time
from pandas import DataFrame
import pandas as pd

def get_xauusd_15min_candles(max_retries=3, delay_seconds=3):
    symbol = "XAUUSD"
    timeframe = mt5.TIMEFRAME_M15

    for attempt in range(1, max_retries + 1):
        print(f"🛠️ Attempt {attempt} ➝ Initializing MetaTrader 5")
        try:
            if not mt5.initialize():
                raise RuntimeError(f"MT5 init failed ➝ {mt5.last_error()}")
            else:
                print("✅ MetaTrader 5 initialized successfully.")
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Symbol selection failed ➝ {mt5.last_error()}")

            candles = mt5.copy_rates_from_pos(symbol, timeframe,1,1)

            mt5.shutdown()

            if candles is None or len(candles) == 0:
                raise ValueError("No candle data retrieved.")

            candle = candles[0]
            open_ = candle['open']
            close = candle['close']
            size = (close - open_)

            print(f"🔍 Sanity Check ➝ Open: {open_}, Close: {close}, Size: {size}")

            if abs(size) < 0.01:
                raise ValueError("Candle too small ➝ retrying...")

            return {
                "open": open_,
                "close": close,
                "high": candle['high'],
                "low": candle['low'],
                "volume": candle['tick_volume'],
                "timestamp": datetime.fromtimestamp(candle['time']).isoformat()
            }

        except Exception as e:
            print(f"⚠️ Error ➝ {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)

    print("❌ All retries failed — no valid candle retrieved.")
    return None


def get_xauusd_init_data(max_retries=3, delay_seconds=3):
    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt} ➝ Initializing MT5")
        try:
            # Step 1: Initialize MT5
            if not mt5.initialize():
                raise RuntimeError(f"MT5 init failed ➝ {mt5.last_error()}")
            print("✅ MT5 initialized successfully.")

            # Step 2: Select XAUUSD
            if not mt5.symbol_select("XAUUSD", True):
                raise RuntimeError(f"Symbol selection failed ➝ {mt5.last_error()}")

            # Step 3: Fetch last 4 candles to ensure 3 are fully closed
            rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 5)
            if rates is None or len(rates) < 3:
                raise ValueError("Not enough candle data retrieved.")

            # Step 4: Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')

            # Step 5: Calculate size = abs(close - open)
            df['size'] = (df['close'] - df['open']).abs()

            # Step 6: Return last 3 fully closed candles
            return df[['time', 'open', 'high', 'low', 'close', 'size']].iloc[-5:-1]

        except Exception as e:
            print(f"⚠️ Error ➝ {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)

    print("❌ All retries failed — no valid candle retrieved.")
    return None