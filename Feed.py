import MetaTrader5 as mt5
from datetime import datetime
import time

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
                "timestamp": datetime.fromtimestamp(candle['time']).isoformat()
            }

        except Exception as e:
            print(f"⚠️ Error ➝ {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)

    print("❌ All retries failed — no valid candle retrieved.")
    return None