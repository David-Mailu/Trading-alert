import socket, time,threading
from datetime import datetime, timedelta

from telebot.apihelper import MAX_RETRIES

import bot
from Feed import get_xauusd_init_data
from Logic import  SRManager
from support import MarketSchedule, CandleFetcher, AlertLogger, Reversal
from bot import  sr_config, send_telegram_alert, start_bot
from Signals import Trend
# 🧠 Smart Alert Server
class SmartServer:

    def get_status_payload(self):
        status ="🟢 active" if self.paused==False else "🔴 paused"

        sr_configuration = {
            "tolerance": self.sr.tolerance,
            "support": self.sr.support,
            "resistance": self.sr.resistance,
            "resistance_liquidity": self.sr.resistance_liquidity,
            "support_liquidity": self.sr.support_liquidity
        }
        tolerance = sr_configuration["tolerance"]
        support = sr_configuration["support"]
        resistance = sr_configuration["resistance"]
        resistance_liquidity = sr_configuration["resistance_liquidity"]
        support_liquidity = sr_configuration["support_liquidity"]

        payload = (
            f"📊 *System Status*\n"
            f"- Alerts: {status}\n"
            f"- Tolerance: `{tolerance}`\n"
            f"- Support Zones: `{', '.join(map(str, support)) or 'None'}`\n"
            f"- Resistance Zones: `{', '.join(map(str, resistance)) or 'None'}`\n"
            f"- Resistance Liquidity Zones: `{', '.join(map(str, resistance_liquidity)) or 'None'}`\n"
            f"- Support Liquidity Zones: `{', '.join(map(str, support_liquidity)) or 'None'}`\n"
        )
        return payload if payload else "⚠️ No data available."

    def pause(self):
        self.paused = True
        print("🔕 alerts_active =", self.paused)
        send_telegram_alert("🔕 *Alert system paused.*")

    def resume(self):
        self.paused= False
        print("✅ alerts_active =", self.paused)
        send_telegram_alert("🔔 *Alert system resumed.*")

    def sync_remote_sr(self, sr_config,max_zones=5):
        self.sr.support_liquidity = sr_config.get("support", [])[:]
        self.sr.resistance_liquidity = sr_config.get("resistance", [])[:]
        self.sr.tolerance = sr_config.get("tolerance", self.sr.tolerance)
        while len(self.sr.support_liquidity) > max_zones:
            self.sr.support_liquidity.pop(0)
        while len(self.sr.resistance_liquidity) > max_zones:
            self.sr.resistance_liquidity.pop(0)
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
          self.sr.support_liquidity=[]
          self.sr.resistance_liquidity = []
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
            if df is not None and len(df) >=13:
                records=df.to_dict('records')
                reversal_buffer=records[-4:]
                base, next1, next2, candle = reversal_buffer
                store_candle=records[-13:]
                print("✅ Initialization successful with fetched candle data.")
                self.sr.reversal_buffer=reversal_buffer
                self.sr.store_candle=store_candle
                print("Reversal buffer and store candle initialized with last 4 candles.")
                if candle:
                  open_ = float(candle["open"])
                  close = float(candle["close"])
                  volume= float(candle["tick_volume"])
                  size = (close - open_)
                  print(f"🔍 Candle Data ➝ Open: {open_}, Close: {close}")
                  direction = "up" if close > open_ else "down"
                  self.sr.prev_dir = direction
                  self.sr.prev_size = size
                  print(f"📈 Previous direction: {direction}")
                  print(f"💡 Previous candle size: {size}")
                  self.sr.get_candle_stats()
                  self.signal.init_trend()

                self.sr.init_reversal_zones()
                return True

            print(f"[Init Retry {attempt}] ❌ No valid candle. Retrying in {delay_seconds}s...")
            time.sleep(delay_seconds)

        print("❌ Initialization failed after retries.")
        return False
    def __init__(self, debug=False,shutdown_event=None):
        self.shutdown_event = shutdown_event
        self.debug = debug
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.bind(('::1', 65432))
        self.sock.listen()
        print("🧠 Server online (IPv6). Waiting for connection...")
        self.conn, addr = self.sock.accept()
        print(f"🔗 Connected to {addr}")

        self.market = MarketSchedule(debug=debug,shutdown_event=shutdown_event)
        self.paused = False
        self.paused_state = False
        self.fetcher = CandleFetcher()
        self.sr = SRManager(self)
        self.signal = Trend(self)
        self.log = AlertLogger(self.conn)
        self.reversal = Reversal()
        self.recent_init=datetime.now()
    def start(self):
        if not self.initialize():
            return
        try:
            while not self.shutdown_event.is_set():
                if self.paused:
                    if not self.paused_state:
                     print("🔕 Server paused. Waiting for resume...")
                    self.paused_state=True
                    if self.shutdown_event.wait(timeout=1):
                        print("Shutdown event detected during pause.")
                        break
                    continue
                else:
                    self.paused_state=False
                try:
                    if not self.market.wait_next_quarter():
                        print("Wait next quarter returned false.")
                        self.log.log("server wait_next_quarter returned false")
                        return

                    candle = self.fetcher.pull()
                    if not candle:
                        return

                    atr, direction = self.sr.start_logic(candle)
                    self.signal.start_signal(atr, direction)

                except Exception as e:
                    print(f"💥 Crash after wait_next_quarter: {e}")
                    self.log.log(f"💥 Crash after wait_next_quarter: {e}")
                    raise  # Let it bubble up to trigger orchestrator restart

                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    self.reset_state(sr_config)

                if self.market.in_maintenance():
                    print("😴 Maintenance window (12AM–1AM). Sleeping...")
                    time.sleep(3600)
                    continue


        except KeyboardInterrupt:
            print("🛑 Server interrupted.")
        except Exception as e:
            print(f"💥 Uncaught error: {e}")
            self.log.log(f"⚠️ *Server error:* `{e}`")
        finally:
            print("🔌 Closing server...")
            self.conn.close()
            self.sock.close()

def run_server():
    try:
        server.start()
    except Exception as e:
        print(f"🚨 Fatal error in server loop: {e}")
        send_telegram_alert(f"🚨 Server crashed: `{e}`")

def run_bot():
    try:
        start_bot()
    except Exception as e:
        print(f"🤖 Bot error: {e}")
        send_telegram_alert(f"⚠️ Bot crashed: `{e}`")

# 🏁 Entrypoint
if __name__ == "__main__":
    MAX_RETRIES=3
    DELAY_SECONDS=5
    bot_retries=0
    server_retries=0
    shutdown_event = threading.Event()
    shutdown_event.clear()
    try:
        server = SmartServer(debug=False,shutdown_event=shutdown_event)
        bot.server_instance = server

        server_thread = threading.Thread(target=run_server, daemon=True)
        bot_thread = threading.Thread(target=run_bot, daemon=True)

        server_thread.start()
        bot_thread.start()

        while True:
            if shutdown_event.is_set():
                print("Shutdown event detected. Exiting orchestrator loop.")
                break
            if not server_thread.is_alive():
                if shutdown_event.is_set():
                    print("Shutdown event detected. Not restarting server thread.")
                    break
                server_retries+=1
                if server_retries > MAX_RETRIES:
                    print("🚨 Server failed to restart after max retries. Exiting...")
                    send_telegram_alert("🚨 *Server failed to restart after max retries. Exiting...*")
                    shutdown_event.set()
                    break
                print("🚨 Server thread crashed.")
                send_telegram_alert("🚨 *Server thread crashed. Restarting...*")
                server_thread = threading.Thread(target=run_server, daemon=True)
                server_thread.start()
                time.sleep(DELAY_SECONDS)
            if not bot_thread.is_alive():
                if shutdown_event.is_set():
                    print("Shutdown event detected. Not restarting bot thread.")
                    break
                bot_retries+=1
                if bot_retries > MAX_RETRIES:
                    print("🚨 Bot failed to restart after max retries. Exiting...")
                    send_telegram_alert("🚨 *Bot failed to restart after max retries. Exiting...*")
                    shutdown_event.set()
                    break
                print("🚨 Bot thread crashed.")
                send_telegram_alert("🚨 *Bot thread crashed. Restarting...*")
                bot_thread = threading.Thread(target=run_bot, daemon=True)
                bot_thread.start()
                time.sleep(DELAY_SECONDS)
            time.sleep(1)

    except KeyboardInterrupt:
        print("🛑 Ctrl+C received. Shutting down...")
    except Exception as e:
        print(f"🚨 Fatal error in orchestrator: {e}")