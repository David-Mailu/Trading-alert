import socket

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 65432))
print("🛎️ Client is listening...")

while True:
    alert = client_socket.recv(1024)
    print(f"\n🚨 SERVER: {alert.decode('utf-8')}")