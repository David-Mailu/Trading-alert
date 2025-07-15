import time
import requests

API_KEY = "6f67bf046e494077a8f8d21927a7c5d9"

def get_xauusd_15min_candles(max_retries=3, delay_seconds=3):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 1,  # Only need the latest candle
        "apikey": API_KEY
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "values" in data and len(data["values"]) > 0:
                candle = data["values"][0]  # Get the latest candle
                return {

                    "open": float(candle["open"]),
                    "close": float(candle["close"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"])


                }
            else:
                raise ValueError(f"No candle data returned: {data}")
        except Exception as e:
            print(f"[Retry {attempt}] ⚠️ TwelveData error: {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                print("❌ Max retries reached. Returning None.")
                return None