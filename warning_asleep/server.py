import cv2
import socket
import struct
import pickle
import numpy as np

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("0.0.0.0", 9999))
server_socket.listen(1)
print("Waiting for client connection...")

conn, addr = server_socket.accept()
print("Client connected:", addr)

cap = cv2.VideoCapture(0)

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
        
        data = pickle.dumps(buffer)
        message = struct.pack("Q", len(data)) + data
        conn.sendall(message)

except Exception as e:
    print(f"Lỗi phía server: {e}")

finally:
    cap.release()
    conn.close()
    server_socket.close()
    print("Server đã đóng.")