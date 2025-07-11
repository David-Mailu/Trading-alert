# Feed.py
import requests
import time

API_KEY = "C0VAORS5QVWWPB9W"

def get_xauusd_price(max_retries=5, delay_seconds=2):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "XAU",
        "to_currency": "USD",
        "apikey": API_KEY
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            rate = data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
            return float(rate)

        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"[Retry {attempt}] ⚠️ Error fetching price: {e}")
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                print("❌ Max retries reached. Returning None.")
                return None