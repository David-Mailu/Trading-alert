import time
from datetime import datetime
import requests

# TwelveData and Finnhub API keys
TWELVE_API_KEY = "6f67bf046e494077a8f8d21927a7c5d9"
FINNHUB_API_KEY = "d1v74vhr01qj71gjro90d1v74vhr01qj71gjro9g"

def try_twelvedata(max_retries=3, delay_seconds=3):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 1,
        "apikey": TWELVE_API_KEY
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "values" in data and len(data["values"]) > 0:
                candle = data["values"][0]

                open_ = float(candle["open"])
                close = float(candle["close"])
                high = float(candle["high"])
                low = float(candle["low"])
                size = abs(close - open_)

                if size < 0.1:
                    print(f"⚠️ TwelveData candle too small ➝ open={open_}, close={close}, size={size}")
                    return None

                return {
                    "open": open_,
                    "close": close,
                    "high": high,
                    "low": low
                }

            else:
                print(f"❌ TwelveData returned empty or invalid candle: {data}")
                return None

        except Exception as e:
            print(f"[TwelveData Retry {attempt}] ⚠️ Error: {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                print("❌ TwelveData max retries reached.")
                return None

def try_finnhub():
    symbol = "OANDA:XAUUSD"
    resolution = "15"
    now = int(time.time())
    start = now - 900  # 15 minutes ago

    print(f"🕒 Finnhub timestamps ➝ from={start}, to={now}")

    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": start,
        "to": now
    }
    headers = {
        "X-Finnhub-Token": FINNHUB_API_KEY
    }

    print("From:", datetime.fromtimestamp(start))
    print("To:", datetime.fromtimestamp(now))
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("s") != "ok" or len(data.get("o", [])) == 0:
            print("⚠️ Finnhub returned no usable candle data.")
            return None

        i = -1  # Last index is the most recent candle
        open_ = float(data["o"][i])
        close = float(data["c"][i])
        high = float(data["h"][i])
        low = float(data["l"][i])
        size = abs(close - open_)

        if size < 0.1:
            print(f"⚠️ Finnhub candle too small ➝ open={open_}, close={close}, size={size}")
            return None

        return {
            "open": open_,
            "close": close,
            "high": high,
            "low": low
        }

    except Exception as e:
        print(f"❌ Finnhub error: {e}")
        return None

def get_xauusd_15min_candles():
    start_time = time.monotonic()

    candle = try_twelvedata()
    if candle:
        print("✅ Candle source: TwelveData")
        return candle

    if time.monotonic() - start_time < 10:
        print("⏱️ Switching to Finnhub due to TwelveData timeout or bad data...")
        fallback = try_finnhub()
        if fallback:
            print("✅ Candle source: Finnhub")
            return fallback

    print("❌ No valid candle from either source.")
    return None