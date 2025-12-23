import socket

HOST = "192.168.50.202"  # The server's hostname or IP address
# doc says 9590, limited success so far with 9596
PORT = 9596  # The port used by the server

addr = (HOST, PORT)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # s.settimeout(5)
    s.connect((HOST, PORT))

    print("Connected!")

    s.sendall(b"amp:power?")
    data = s.recv(1024)

print(f"Received {data!r}")