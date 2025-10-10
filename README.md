# 📊 Trading-Alert System

An intelligent server-client alert system for monitoring XAUUSD price movements and providing real-time notifications on volatility, reversals, and support/resistance (SR) breaks.

Created by [David-Mailu](https://github.com/David-Mailu), this system began as a simple alert engine and is evolving into a modular, antifragile trading bot. It leverages Python’s socket programming, threading, and defensive design to deliver fast, focused alerts for disciplined traders.

---

## 🚀 Project Overview

This system is designed to:

- Monitor real-time XAUUSD candles via automated feed.
- Detect high volatility and directional momentum.
- Identify SR zones and notify when broken by cumulative price action.
- Filter noisy signals using candle similarity and clustering logic.
- Send alerts to both local client and Telegram bot.
- Maintain antifragile logic through journaling, fallback alerting, and timestamp validation.

---

## 🧱 Architecture

| Module              | Role                                                                 |
|---------------------|----------------------------------------------------------------------|
| `ServerManager.py`  | Central orchestrator running the main polling loop and alert logic.  |
| `client.py`         | Passive socket-based listener for local notifications.               |
| `Feed.py`           | Candle data acquisition module (e.g. TwelveData, MT5).               |
| `Logic.py`          | Reversal detection, SR zone management, and volatility scoring.      |
| `Signals.py`        | Signal engine including Trend, SRManager, and Reversal modules.      |
| `support.py`        | Utilities for market scheduling, logging, and alert handling.        |
| `Bot.py`            | Telegram bot integration for remote control and alert dispatch.      |

---

## 🧠 Core Features

| Feature                     | Description                                                                                |
|-----------------------------|--------------------------------------------------------------------------------------------|
| 🧠 Reversal Detection       | Identifies directional reversals and pullbacks using candle patterns.                      |
| 🔔 SR Break Confirmation    | Detects and buffers break events based on cumulative size logic.                           |
| 📏 Directional Validation   | Ensures breaks only trigger when movement aligns with zone type (up/down).                 |
| 🧱 Dynamic SR Zones         | User-defined support and resistance levels with live recalibration.                        |
| 🗜️ Cumulative Break Filter | Only sends alerts when SR break size exceeds dynamic tolerance across consecutive candles. |
| 🔂 Wick Filtering           | Filters out misleading SR breaks caused by candle wicks.                                   |
| 📊 Consolidation Detection  | Flags tight range activity between defined support and resistance.                         |
| 📤 Telegram Integration     | Sends all qualified alerts to Telegram bot in real-time.                                   |
| 🧠 Volatility Scoring       | Calculates ATR, ATS, and volume indices to assess momentum and breakout strength.          |
| 🧠 Signal Journaling        | Logs every signal with contextual stats for post-trade analysis and system evolution.       |

---

## 🤖 Telegram Bot Integration & Control

The system includes a dedicated `Bot.py` module for enhanced user interaction via Telegram. It allows for real-time control and feedback through chat commands.

### 🧭 Commands

- `/pause` – Pauses alert dispatch (`server_instance.alerts_active = False`)
- `/resume` – Reactivates alerts (`server_instance.alerts_active = True`)
- `/status` – Returns current system status including alert state, active feed, and last alert time

### 🛠️ Code Integration Note

All alert-state checks should now use:

```python
if not server.alerts_active:
    print("🔕 Alert skipped: system is paused.")
## 📦 Installation & Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/David-Mailu/Trading-alert.git