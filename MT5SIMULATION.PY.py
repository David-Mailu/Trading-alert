import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, timezone

# Step 1: Initialize MT5
if not mt5.initialize():
    print("MT5 initialization failed:", mt5.last_error())
    quit()
mt5.symbol_select("XAUUSD", True)

# Step 3: Fetch 15-minute candles for XAUUSD
rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15,1,1)

# Step 4: Convert to DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

# Step 5: Calculate size = abs(close - open)
df['size'] = (df['close'] - df['open']).abs()

# Step 6: Select and print last 3 candles
print(df[['time', 'open', 'high', 'low', 'close', 'size']].tail(3))
