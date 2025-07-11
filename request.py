import requests

API_KEY = "YOUR_NEW_API_KEY"
url = "https://www.alphavantage.co/query"
params = {
    "function": "CURRENCY_EXCHANGE_RATE",
    "from_currency": "USD",
    "to_currency": "XAU",
    "apikey": API_KEY
}

response = requests.get(url, params=params)
data = response.json()
print(data)