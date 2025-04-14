import socket
import json
import pyaudio
from vosk import Model, KaldiRecognizer

HOST = '192.168.135.46'
PORT = 12345

# Load mô hình tiếng Anh
model = Model("vosk-model-small-en-us-0.15")

# Thiết lập nhận diện
rec = KaldiRecognizer(model, 16000)

# Thiết lập micro
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, 
                channels=1, rate=16000, 
                input=True, 
                frames_per_buffer=8192)
stream.start_stream()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def record_and_convert_to_text_vosk():
    print("Nói gì đó...")
    data = stream.read(4096)
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        text = result.get("text", "")
        if text:
            print(f"Bạn đã nói: {text}")
            return text
    return None

def send_to_server():
    try:
        while True:
            text = record_and_convert_to_text_vosk()
            if text:
                client_socket.sendto(text.encode('utf-8'), (HOST, PORT))
                print(f"Đã gửi: {text}")
                print(type(text.encode('utf-8')))

    except KeyboardInterrupt:
        print("Dừng chương trình.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    send_to_server()