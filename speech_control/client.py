import socket
import json
import pyaudio
from vosk import Model, KaldiRecognizer
import time

# Information of server
HOST = '192.168.137.53'
PORT = 12345

# Load Model Vosk
model = Model(r'.\speech_control\vosk-model-small-en-us-0.15')
rec = KaldiRecognizer(model, 16000)

# Set up audio stream
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, 
                channels=1, rate=16000, 
                input=True, 
                frames_per_buffer=8192)
stream.start_stream()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def record_and_convert_to_text_vosk():
    print("Recording for 1 second...")
    audio_data = b''
    start_time = time.time()
    while time.time() - start_time < 1:
        data = stream.read(4096, exception_on_overflow=False)
        audio_data += data

    if rec.AcceptWaveform(audio_data):
        result = json.loads(rec.Result())
        text = result.get("text", "")
        if text:
            print(f"You said: {text}")
            return text
    else:
        result = json.loads(rec.PartialResult())
        print(f"Listen: {result.get('partial', '')}")
    return None

def send_to_server():
    try:
        while True:
            text = record_and_convert_to_text_vosk()
            if text:
                client_socket.sendto(text.encode('utf-8'), (HOST, PORT))
                print(f"Sent: {text}")
    except KeyboardInterrupt:
        print("Stop program.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    send_to_server()
