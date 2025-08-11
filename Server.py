import socket, time,threading
from datetime import datetime, timedelta
from pytz import timezone

import bot
from Feed import get_xauusd_15min_candles
from Telegramalert import send_telegram_alert
from requests.exceptions import RequestException
from Logic import Reversal, SRManager
from support import MarketSchedule, CandleFetcher, AlertLogger
from bot import  sr_config, send_telegram_alert, start_bot

# 🧠 Smart Alert Server
class SmartServer:
    def get_status_payload(self):
        payload=self.sr.get_status_payload()
        return payload if payload else "⚠️ *No status data available.*"

    def pause(self):
        self.paused = True
        print("🔕 alerts_active =", self.paused)
        send_telegram_alert("🔕 *Alert system paused.*")

    def resume(self):
        self.paused=False
        print("✅ alerts_active =", self.paused)
        send_telegram_alert("🔔 *Alert system resumed.*")
    def sync_remote_sr(self, sr_config):
        self.sr.support = sr_config.get("support", [])[:]
        self.sr.resistance = sr_config.get("resistance", [])[:]
        self.sr.tolerance = sr_config.get("tolerance", self.sr.tolerance)
        print("🔗 Synced SR zones from remote config.")

    def reset_state(self):
        print("Executing server reset...")
        try:
          print("🔄 Resetting internal server state...")
          self.reversal_buffer = []
          self.prev_dir = None
          self.prev_size = None
          self.last_break = None
          self.reversal.consolidation_count = 0
          self.sr.breaks = {"support": [], "resistance": []}
          self.sr.bounces = {"support": [], "resistance": []}
          self.sr.resistance= []
          self.sr.support = []
          self.sr.break_buffer_detailed={
                "support": {},  # Format: {zone_price: [size1, size2, ...]}
                "resistance": {}
          }
          print("✅ Server state reset complete.")
        except Exception as e:
            print(f"server reset failed: {e}")
            msg= f"⚠️ *Server reset failed:* `{e}`"
            send_telegram_alert(msg)
    def initialize(self, max_retries=3, delay_seconds=4):
        if not self.market.is_market_open():
            print("📴 Market closed. Exit.")
            return False

        self.sr.init_zones()
        print("📥 Auto-fetching last candle for initialization...")

        for attempt in range(1, max_retries + 1):
            candle = get_xauusd_15min_candles()
            if candle:
                open_ = candle["open"]
                close = candle["close"]
                size = abs(close - open_)
                direction = "up" if close > open_ else "down"

                self.prev_dir = direction
                self.prev_size = size

                print(f"📈 Previous direction: {direction}")
                print(f"💡 Previous candle size: {size}")
                return True

            print(f"[Init Retry {attempt}] ❌ No valid candle. Retrying in {delay_seconds}s...")
            time.sleep(delay_seconds)

        print("❌ Initialization failed after retries.")
        return False
    def __init__(self, debug=False):
        self.debug = debug
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.bind(('::1', 65432))
        self.sock.listen()
        print("🧠 Server online (IPv6). Waiting for connection...")
        self.conn, addr = self.sock.accept()
        print(f"🔗 Connected to {addr}")

        self.market = MarketSchedule(debug=debug)
        self.paused = False
        self.fetcher = CandleFetcher()
        self.sr = SRManager(self)
        self.log = AlertLogger(self.conn)
        self.reversal = Reversal()
        self.reversal_buffer = []
        self.prev_dir = None
        self.prev_size = None
        self.last_break = None
        self.sr_config = sr_config

    def wait_next_quarter(self):
        now = datetime.now()
        minute = ((now.minute // 15 + 1) * 15) % 60
        hour = (now.hour + (1 if minute == 0 else 0)) % 24
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        sleep = (next_time - now).total_seconds()
        print(f"⏳ Next run at {next_time.strftime('%H:%M')} ({int(sleep)}s)")
        time.sleep(sleep)



    def check_sr_breaks(self, candle, price, size, direction):
        for typ in ["support", "resistance"]:
            zone = self.sr.nearest_zone(price, typ)
            if zone and self.sr.is_valid_break(candle, typ, zone):
                self.sr.add_break(typ, zone, size)
                msg = f"📉 Support broken near ${zone} ➞ ${price}" if typ == "support" else \
                      f"📈 Resistance broken near ${zone} ➞ ${price}"
                self.log.log(msg)

        if not self.sr.support and not self.sr.resistance:
              print("⚠️ SR zones missing — syncing from remote config.")
              time.sleep(60)
              self.sync_remote_sr(sr_config)  # or however your config is passed
    def start(self):
        if not self.initialize():
            return
        try:
            while True:
                if self.paused:
                    print("🔕 Server paused. Waiting for resume...")
                    time.sleep(1)
                    continue
                self.wait_next_quarter()
                # ⏰ Local time-based reset at midnight
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    self.reset_state()

                if self.market.in_maintenance():
                    print("😴 Maintenance window (12AM–1AM). Sleeping...")
                    time.sleep(3600)
                    continue

                candle = self.fetcher.pull()
                if not candle:
                    continue

                open_, close = float(candle["open"]), float(candle["close"])
                size = abs(close - open_)
                price = close
                direction = "up" if close > open_ else "down"

                # ✅ Early SR break check
                self.check_sr_breaks(candle, price, size, direction)

                # 🧠 Reversal logic
                self.reversal_buffer.append(candle)
                if len(self.reversal_buffer) > 3:
                    self.reversal_buffer.pop(0)

                if len(self.reversal_buffer) == 3:
                    base, next1, next2 = self.reversal_buffer
                    msgs = []

                    m1 = self.reversal.is_downward_reversal(base, [next1, next2])
                    if m1: msgs.append(m1)

                    m2 = self.reversal.is_upward_reversal(base, [next1, next2])
                    if m2: msgs.append(m2)

                    m3 = self.reversal.is_pullback_reversal(
                        "up" if base["close"] > base["open"] else "down",
                        [next1, next2]
                    )
                    if m3: msgs.append(m3)

                    for msg in msgs:
                        self.log.log(msg)

                    msg = self.reversal.detect_consolidation(self.reversal_buffer)
                    if msg:
                        self.log.log(msg)

                # 🛡️ SR Zone Interaction
                for typ in ["support", "resistance"]:
                    zone = self.sr.nearest_zone(price, typ)
                    if zone:
                        self.sr.record_bounce(typ, zone, price)

                # 📊 Consolidation signal (based on bounces)
                if all(len(self.sr.bounces[t]) >= 5 for t in ["support", "resistance"]):
                    msg = (
                        f"📊 Consolidation detected between "
                        f"Support ≈ ${self.sr.nearest_zone(price, 'support')} and "
                        f"Resistance ≈ ${self.sr.nearest_zone(price, 'resistance')}"
                    )
                    self.log.log(msg)
                    self.sr.bounces = {"support": [], "resistance": []}

                # 🔔 SR break report if combined size > 5
                for typ in ["support", "resistance"]:
                    messages = self.sr.report_strong_breaks(typ)
                    for msg in messages:
                        self.log.log(msg)

                # ⚡ Volatility / Momentum Notifications
                if size > 5:
                    msg = f"⚡ High Volatility! Size: ${size}"
                    self.log.log(msg)
                else:
                    similar = (
                        self.prev_size and abs(size - self.prev_size) < 0.5
                        and direction == self.prev_dir
                    )
                    clustered = (
                        self.last_break and datetime.now() - self.last_break < timedelta(minutes=30)
                    )

                    if similar or clustered:
                        print("🚫 Skipping volatility alert due to similar candle or recent SR break.")
                    else:
                        zone_r = self.sr.nearest_zone(price, "resistance")
                        zone_s = self.sr.nearest_zone(price, "support")

                        if zone_r and price > zone_r:
                            msg = f"📈 Resistance broken near ${zone_r} ➞ ${price}"
                            self.last_break = datetime.now()
                            self.log.log(msg)

                        elif zone_s and price < zone_s:
                            msg = f"📉 Support broken near ${zone_s} ➞ ${price}"
                            self.last_break = datetime.now()
                            self.log.log(msg)

                        else:
                           continue

                # ✅ Second/failsafe SR break check
                self.check_sr_breaks(candle, price, size, direction)

                # Update previous cycle state
                self.prev_dir, self.prev_size = direction, size

        except KeyboardInterrupt:
            print("🛑 Server interrupted.")
        except Exception as e:
            print(f"💥 Uncaught error: {e}")
            send_telegram_alert(f"⚠️ *Server error:* `{e}`")
            self.log.log(f"⚠️ *Server error:* `{e}`")
            self.reset_state()
        finally:
            send_telegram_alert("🔌 *Server shutting down.")
            print("🔌 Closing server...")
            self.conn.close()
            self.sock.close()

# 🏁 Entrypoint
if __name__ == "__main__":
    try:
        server = SmartServer(debug=False)
        bot.server_instance = server
        threading.Thread(target=start_bot, daemon=True).start()
        server.start()
    except Exception as e:
        print(f"🚨 Fatal error in orchestrator: {e}")