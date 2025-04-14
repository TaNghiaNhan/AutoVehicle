import socket
import cv2
import pickle
import struct
import threading

# Tạo socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
port = 9999
socket_address = ('192.168.157.36', port)

server_socket.bind(socket_address)
server_socket.listen(5)
print(f"Server đang chạy tại {socket_address}")

# Khởi tạo webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Giảm độ phân giải
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

def handle_client(client_socket, addr):
    print(f"Kết nối từ: {addr}")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Resize frame để giảm kích thước
        frame = cv2.resize(frame, (320, 240))
        # Nén frame thành JPEG
        result, frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        data = pickle.dumps(frame)
        message_size = struct.pack("L", len(data))
        
        try:
            client_socket.sendall(message_size + data)
        except:
            print(f"Client {addr} ngắt kết nối")
            break
    client_socket.close()

while True:
    client_socket, addr = server_socket.accept()
    thread = threading.Thread(target=handle_client, args=(client_socket, addr))
    thread.start()

cap.release()
server_socket.close()