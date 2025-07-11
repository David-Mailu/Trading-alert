# client.py
import socket
from datetime import datetime

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 65432))
print("📡 Connected to server. Awaiting alerts...\n")

with open("alerts_log.txt", "a") as log_file:
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        message = data.decode('utf-8')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted = f"[{timestamp}] {message}"

        print(formatted)
        log_file.write(formatted + "\n")