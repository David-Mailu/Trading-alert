import socket
import time
from datetime import datetime

def connect_to_server(timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            client_socket.connect(('::1', 65432))
            print("📡 Connected to server via IPv6.")
            return client_socket
        except OSError:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect(('127.0.0.1', 65432))
                print("📡 Connected to server via IPv4.")
                return client_socket
            except OSError:
                print("🔌 Server unreachable. Retrying in 10s...")
                time.sleep(10)
    print("🛑 Connection failed: Server not available after 60s.")
    return None

def listen_for_alerts(socket_obj):
    print("🧠 Awaiting alerts...\n")
    try:
        with open("alerts_log.txt", "a", encoding="utf-8") as log_file:
            while True:
                data = socket_obj.recv(1024)
                if not data:
                    print("📴 Server closed connection.")
                    break
                message = data.decode('utf-8')
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                formatted = f"[{timestamp}] {message}"
                print(formatted)
                log_file.write(formatted + "\n")
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
        raise  # Let outer loop handle shutdown
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    finally:
        print("🔌 Closing client socket...")
        try:
            socket_obj.close()
        except:
            pass

def persistent_client():
    while True:
        client_socket = connect_to_server()
        if not client_socket:
            print("🛑 Giving up after timeout.")
            break

        try:
            listen_for_alerts(client_socket)
        except KeyboardInterrupt:
            print("🛑 Client shutdown requested.")
            break
        except Exception as e:
            print(f"⚠️ Listener error: {e}. Reconnecting in 5s...")
            time.sleep(5)
            continue

if __name__ == "__main__":
    try:
        persistent_client()
    except KeyboardInterrupt:
        print("🛑 Client terminated by user.")