import time
import requests

API_KEY = "6f67bf046e494077a8f8d21927a7c5d9"

def get_xauusd_price(max_retries=3, delay_seconds=3):
    url = "https://api.twelvedata.com/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": API_KEY
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "price" in data:
                return float(data["price"])
            else:
                raise ValueError(f"No price returned: {data}")
        except Exception as e:
            print(f"[Retry {attempt}] ⚠️ TwelveData error: {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                print("❌ Max retries reached. Returning None.")
                return None