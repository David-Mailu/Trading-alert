# 📊 Trading-Alert System

An intelligent server-client alert system for monitoring XAUUSD price movements and providing real-time notifications on volatility, reversals, and support/resistance (SR) breaks.

Created by [David-Mailu](https://github.com/David-Mailu), this system leverages Python’s socket programming and modular design to deliver fast, focused alerts for disciplined traders.

---

## 🚀 Project Overview

This system is designed to:

- Monitor real-time XAUUSD candles via automated feed.
- Detect high volatility and directional momentum.
- Identify SR zones and notify when broken by cumulative price action.
- Filter noisy signals using candle similarity and clustering logic.
- Send alerts to both local client and Telegram bot.

### 🧱 Architecture

- `ServerManager.py`: Central orchestration class running alert logic.
- `client.py`: Passive socket-based listener for notifications.
- `Feed.py`: Candle data acquisition module (e.g. from TwelveData).
- `Logic.py`: Contains reversal detection and SR zone management.
- `support.py`: Utilities including market scheduling and alert handling.
- `Telegramalert.py`: Sends real-time alerts to configured Telegram bot.

---

## 🧠 Core Features

| Feature                     | Description                                                                 |
|----------------------------|------------------------------------------------------------------------------|
| 🧠 Reversal Detection       | Identifies directional reversals and pullbacks using candle patterns.       |
| 🔔 SR Break Confirmation    | Detects and buffers break events based on cumulative size logic.            |
| 📏 Directional Validation   | Ensures breaks only trigger when movement aligns with zone type (up/down). |
| 🧱 Static SR Zones          | User-defined support and resistance levels with no live recalibration.     |
| 🗜️ Cumulative Break Filter | Only sends alerts when SR break size exceeds $5 across consecutive candles. |
| 🔂 Wick Filtering           | Filters out misleading SR breaks caused by candle wicks.                   |
| 📊 Consolidation Detection | Flags tight range activity between defined support and resistance.         |
| 📤 Telegram Integration     | Sends all qualified alerts to Telegram bot in real-time.                    |

---

## 📦 Installation & Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/David-Mailu/Trading-alert.git