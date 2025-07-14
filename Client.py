import socket
from datetime import datetime

# 🌐 Create a dual-stack socket (try IPv6, fallback to IPv4 loopback)
try:
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    client_socket.connect(('::1', 65432))
    print("📡 Connected to server via IPv6.")
except OSError:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 65432))
    print("📡 Connected to server via IPv4.")

print("🧠 Awaiting alerts...\n")

with open("alerts_log.txt", "a", encoding="utf-8") as log_file:
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        message = data.decode('utf-8')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted = f"[{timestamp}] {message}"

        print(formatted)
        log_file.write(formatted + "\n")

client_socket.close()