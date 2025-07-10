# 📊 Trading-Alert System

An intelligent server-client alert system for monitoring XAUUSD price movements and providing real-time notifications on volatility and support/resistance (SR) breaks.

Created by [David-Mailu](https://github.com/David-Mailu), this system leverages Python’s socket programming to build an efficient local communication framework for traders.

---

## 🚀 Project Overview

This system is designed to:
- Monitor live XAUUSD prices manually entered by the trader.
- Detect high volatility and alert the client.
- Identify SR levels and notify when broken.
- Filter noisy signals using candle similarity and clustering logic.

It consists of:
- `server.py`: Smart logic engine that receives user input and broadcasts actionable alerts.
- `client.py`: Passive alert listener displaying server-sent notifications in real time.

---

## 🧠 Core Features

| Feature | Description |
|--------|-------------|
| 🧭 Direction Tracking | Automatically determines whether the price moved up or down. |
| ⚡ Volatility Detector | Sends alerts when candle size exceeds set threshold. |
| 📈📉 SR Break Alerts | Notifies when price crosses predefined support or resistance levels. |
| 🔄 Monitoring Control | Pause/resume monitoring based on trade status. |
| 🚫 Noise Filtering | Blocks repeated alerts for similar candles or clustered SR breaks. |

---

## 📦 Installation & Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/David-Mailu/Trading-alert.git