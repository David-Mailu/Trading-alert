import time
import requests

TWELVE_API_KEY = "6f67bf046e494077a8f8d21927a7c5d9"

def get_xauusd_15min_candles(max_retries=3, delay_seconds=3):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 1,
        "apikey": TWELVE_API_KEY
    }

    for attempt in range(1, max_retries + 1):
        print(f"📡 Attempt {attempt} ➝ Fetching XAU/USD 15min candle")
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "values" in data and len(data["values"]) > 0:
                candle = data["values"][0]
                open_ = float(candle["open"])
                close = float(candle["close"])
                size = abs(close - open_)

                print(f"🔍 Sanity Check ➝ Open: {open_}, Close: {close}, Size: {size}")

                if size < 0.1:
                    print("⚠️ Candle too small ➝ retrying...")
                else:
                    return {
                        "open": open_,
                        "close": close,
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "timestamp": candle["datetime"]
                    }
            else:
                print(f"⚠️ Invalid response ➝ {data}")

        except Exception as e:
            print(f"⚠️ Error ➝ {e}")

        if attempt < max_retries:
            time.sleep(delay_seconds)

    print("❌ All retries failed — no valid candle retrieved.")
    return None

# Run it
