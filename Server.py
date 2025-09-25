import socket, time,threading
from datetime import datetime, timedelta
import bot
from Feed import get_xauusd_init_data
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
        self.paused= False
        print("✅ alerts_active =", self.paused)
        send_telegram_alert("🔔 *Alert system resumed.*")

    def sync_remote_sr(self, sr_config,max_zones=5):
        self.sr.support = sr_config.get("support", [])[:]
        self.sr.resistance = sr_config.get("resistance", [])[:]
        self.sr.tolerance = sr_config.get("tolerance", self.sr.tolerance)
        while len(self.sr.support) > max_zones:
            self.sr.support.pop(0)
        while len(self.sr.resistance) > max_zones:
            self.sr.resistance.pop(0)
        print("🔗 Synced SR zones from remote config.")

    def reset_state(self,sr_config):
        print("Executing server reset...")
        try:
          print("🔄 Resetting internal server state...")
          self.sr.prev_dir = None
          self.sr.prev_size = 0
          self.sr.last_break = None
          self.reversal.consolidation_count = 0
          self.sr.breaks = {"support": {"doji":0,"momentum":0,"high_volatility":0}, "resistance": {"doji":0,"momentum":0,"high_volatility":0}}
          self.sr.bounces = {"support": [], "resistance": []}
          self.sr.red_candles = []
          self.sr.green_candles = []
          self.sr.support=[]
          self.sr.resistance = []
          self.sr.candle_size = []
          self.sr.last_candle = None
          sr_config["tolerance"] = 2.1
          sr_config["support"] = []
          sr_config["resistance"] = []
          self.sr.break_buffer_detailed["support"].clear()
          self.sr.break_buffer_detailed["resistance"].clear()
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
            df= get_xauusd_init_data()
            if df is not None and len(df) >= 4:
                records=df.to_dict('records')[-4:]
                base,next1,next2,candle=records
                print("✅ Initialization successful with fetched candle data.")
                self.sr.reversal_buffer=[base,next1,next2,candle]
                self.sr.store_candle=[base,next1,next2,candle]
                print("Reversal buffer and store candle initialized with last 4 candles.")
                if candle:
                  open_ = float(candle["open"])
                  close = float(candle["close"])
                  size = (close - open_)
                  print(f"🔍 Candle Data ➝ Open: {open_}, Close: {close}")
                  direction = "up" if close > open_ else "down"
                  if direction=="up":
                    self.sr.green_candles.append(size)
                  elif direction=="down":
                    self.sr.red_candles.append(size)
                  else:
                      print("❌ Candle has no direction. Initialization failed.")
                      return False
                  self.sr.prev_dir = direction
                  self.sr.prev_size = size
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
        self.paused_state = False
        self.fetcher = CandleFetcher()
        self.sr = SRManager(self)
        self.log = AlertLogger(self.conn)
        self.reversal = Reversal()

    def start(self):
        if not self.initialize():
            return
        try:
            while True:
                if self.paused:
                    if not self.paused_state:
                     print("🔕 Server paused. Waiting for resume...")
                    self.paused_state=True
                    time.sleep(1)
                    continue
                else:
                    self.paused_state=False
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
                self.sr.start_logic(candle)

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