import socket
import cv2
import pickle
import struct
import numpy as np

# Tạo socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.29.230'  # Thay bằng IP của server
port = 9999
client_socket.connect((host_ip, port))

data = b""
payload_size = struct.calcsize("L")
buffer_size = 16384  # Tăng buffer size

while True:
    try:
        # Nhận dữ liệu
        while len(data) < payload_size:
            data += client_socket.recv(buffer_size)
        
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("L", packed_msg_size)[0]
        
        while len(data) < msg_size:
            data += client_socket.recv(buffer_size)
        
        frame_data = data[:msg_size]
        data = data[msg_size:]
        
        # Deserialize và giải nén frame
        frame = pickle.loads(frame_data)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        
        # Hiển thị frame
        cv2.imshow('Webcam từ Server', frame)
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    except Exception as e:
        print(f"Lỗi: {e}")
        break

client_socket.close()
cv2.destroyAllWindows()