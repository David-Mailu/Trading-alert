import socket, time,threading
from datetime import datetime, timedelta
import bot
from Feed import get_xauusd_15min_candles
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
        Max_support_zones=4
        Max_resistance_zones=4
        while len(self.sr.support) > Max_support_zones:
            self.sr.support.pop()
        while len(self.sr.resistance) > Max_resistance_zones:
            self.sr.resistance.pop()
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

        print("📥 Auto-fetching last candle for initialization...")

        for attempt in range(1, max_retries + 1):
            candle = get_xauusd_15min_candles()
            if candle:
                open_ = candle["open"]
                close = candle["close"]
                size = (close - open_)
                direction = "up" if close > open_ else "down"

                self.prev_dir = direction
                self.prev_size = size

                print(f"📈 Previous direction: {direction}")
                print(f"💡 Previous candle size: {size}")
                self.sr.init_zones()
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
        self.last_color = None
        self.sr_config = sr_config

    def start(self):
        if not self.initialize():
            return
        try:
            while True:
                if self.paused:
                    print("🔕 Server paused. Waiting for resume...")
                    time.sleep(1)
                    continue
                self.market.wait_next_quarter()
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
                size = (close - open_)
                price = close
                direction = "up" if close > open_ else "down"
                color= "white" if direction is None else "green" if direction=="up" else "red"

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

                    m3 = self.reversal.is_pullback_reversal([next1, next2],
                        "up" if base["close"] > base["open"] else "down",

                    )
                    if m3: msgs.append(m3)

                    for msg in msgs:
                        self.log.log(msg)

                    msg = self.reversal.detect_consolidation(self.reversal_buffer)
                    if msg:
                        self.log.log(msg)

                self.sr.check_break(price, size, direction)
                # ⚡ Volatility / Momentum Notifications
                if (abs(self.prev_size)+abs(size)) > 10 and direction == self.prev_dir:
                    msg = f"⚡ High Volatility! Size: ${self.prev_size+size}"
                    self.log.log(msg)
                else:
                    similar = (
                        self.prev_size and abs(abs(size) - abs(self.prev_size)) < 0.5
                        and direction == self.prev_dir
                    )
                    clustered = (
                        self.last_break and datetime.now() - self.last_break < timedelta(minutes=30)
                    )

                    if similar or clustered:
                        print("🚫 Skipping volatility alert due to similar candle or recent SR break.")

                self.sr.check_break(price, size, direction)


                # Update previous cycle state
                self.prev_dir, self.prev_size,self.last_color = direction, size, color

        except KeyboardInterrupt:
            print("🛑 Server interrupted.")
        except Exception as e:
            print(f"💥 Uncaught error: {e}")
            send_telegram_alert(f"⚠️ *Server error:* `{e}`")
            self.log.log(f"⚠️ *Server error:* `{e}`")
            self.reset_state()
        finally:
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