import RPi.GPIO as GPIO
import socket
import cv2
import pickle
import struct
import numpy as np
import time
import mediapipe as mp
import pygame
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Setup GPIO
MOTOR_A = {'IN1': 5, 'IN2': 6, 'ENA': 13}  # Motor Right
MOTOR_B = {'IN3': 19, 'IN4': 26, 'ENB': 12}  # Motor Left

# Setup socket
HOST_IP = '192.168.137.1'
PORT = 9999
BUFFER_SIZE = 16384

# Configuration for drowsiness detection
EYE_CLOSED_THRESHOLD = 0.2
ALERT_TIME = 1.5
ALERT_SOUND = r"/home/bao/Desktop/Connect_Camera/alert.mp3"

# Index of points around the eyes
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Base speed for the motors
BASE_SPEED = 50

pwm_a, pwm_b = None, None
stop_event = threading.Event()
eye_closed_time = None
alert_triggered = False

# ==================== GPIO SETUP ====================
def initialize_gpio():
    """Initialize GPIO and PWM for motors."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in [MOTOR_A['IN1'], MOTOR_A['IN2'], MOTOR_A['ENA'],
                MOTOR_B['IN3'], MOTOR_B['IN4'], MOTOR_B['ENB']]:
        GPIO.setup(pin, GPIO.OUT)
    pwm_a = GPIO.PWM(MOTOR_A['ENA'], 100)
    pwm_b = GPIO.PWM(MOTOR_B['ENB'], 100)
    pwm_a.start(0)
    pwm_b.start(0)
    return pwm_a, pwm_b

# ==================== MOTOR CONTROL ====================
def set_motor(motor, speed, direction):
    """Control the motor with specific speed and direction"""
    speed = max(min(speed, 30), 0)
    if motor == "motor1":
        pwm = pwm_a
        in1, in2 = MOTOR_A['IN1'], MOTOR_A['IN2']
    elif motor == "motor2":
        pwm = pwm_b
        in1, in2 = MOTOR_B['IN3'], MOTOR_B['IN4']
    else:
        return

    try:
        if direction == "forward":
            GPIO.output(in1, GPIO.HIGH)
            GPIO.output(in2, GPIO.LOW)
        elif direction == "backward":
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.HIGH)
        else:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
        pwm.ChangeDutyCycle(speed)
        logger.debug(f"Set {motor} to speed {speed}, direction {direction}")
    except Exception as e:
        logger.error(f"Error setting motor {motor}: {e}")

def move_forward():
    set_motor("motor1", BASE_SPEED, "forward")
    set_motor("motor2", BASE_SPEED, "forward")
    logger.info("Moving forward")

def stop():
    set_motor("motor1", 0, "stop")
    set_motor("motor2", 0, "stop")
    logger.info("Stopped")

# ==================== SOCKET SETUP ====================
def initialize_socket():
    """Initialize and connect the client socket."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST_IP, PORT))
        logger.info("Connected to server.")
        return client_socket
    except Exception as e:
        logger.error(f"Unable to connect to server: {e}")
        raise

# ==================== MEDIAPIPE SETUP ====================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# ==================== SOUND SETUP ====================
def play_sound(file_path):
    """Phát âm thanh cảnh báo."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
    except Exception as e:
        logger.error(f"Error while playing sound: {e}")

# ==================== DROWSINESS DETECTION ====================
def eye_aspect_ratio(eye_landmarks, landmarks):
    """Calculate the Eye Aspect Ratio (EAR) for the given eye landmarks."""
    A = np.linalg.norm(np.array(landmarks[eye_landmarks[1]]) - np.array(landmarks[eye_landmarks[5]]))
    B = np.linalg.norm(np.array(landmarks[eye_landmarks[2]]) - np.array(landmarks[eye_landmarks[4]]))
    C = np.linalg.norm(np.array(landmarks[eye_landmarks[0]]) - np.array(landmarks[eye_landmarks[3]]))
    ear = (A + B) / (2.0 * C)
    return ear

def drowsiness_detection_thread(client_socket):
    global eye_closed_time, alert_triggered
    data = b""
    payload_size = struct.calcsize("Q")

    while not stop_event.is_set():
        try:
            while len(data) < payload_size:
                recv_data = client_socket.recv(BUFFER_SIZE)
                if not recv_data:
                    raise ConnectionError("Lost connection while receiving data size.")
                data += recv_data

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                recv_data = client_socket.recv(BUFFER_SIZE)
                if not recv_data:
                    raise ConnectionError("Lost connection while receiving frame.")
                data += recv_data

            frame_data = data[:msg_size]
            data = data[msg_size:]

            if not frame_data:
                logger.warning("No frame data received from server.")
                continue

            buffer = pickle.loads(frame_data)
            frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning("Unable to decode JPEG buffer.")
                continue

            # Solve the frame with MediaPipe FaceMesh
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = {i: (int(face_landmarks.landmark[i].x * frame.shape[1]),
                                     int(face_landmarks.landmark[i].y * frame.shape[0])) for i in range(468)}
                    left_EAR = eye_aspect_ratio(LEFT_EYE, landmarks)
                    right_EAR = eye_aspect_ratio(RIGHT_EYE, landmarks)
                    avg_EAR = (left_EAR + right_EAR) / 2.0

                    logger.info(f"EAR Average: {avg_EAR:.3f}")

                    if avg_EAR < EYE_CLOSED_THRESHOLD:
                        if eye_closed_time is None:
                            eye_closed_time = time.time()
                        elif time.time() - eye_closed_time > ALERT_TIME and not alert_triggered:
                            logger.warning("Warning: User may be sleepy!!!")
                            play_sound(ALERT_SOUND)
                            stop()
                            alert_triggered = True
                    else:
                        eye_closed_time = None
                        alert_triggered = False
                        logger.info("Status: Open eyes")
                        break
            else:
                logger.info("No face detected")
                move_forward()

        except Exception as e:
            logger.error(f"Error while solving frame: {e}")
            stop_event.set()
            break

# ==================== MAIN FUNCTION ====================
def main():
    global pwm_a, pwm_b
    client_socket = initialize_socket()
    pwm_a, pwm_b = initialize_gpio()

    try:
        move_forward()

        drowsiness_thread = threading.Thread(target=drowsiness_detection_thread, args=(client_socket,))
        drowsiness_thread.start()

        drowsiness_thread.join()

    except KeyboardInterrupt:
        logger.info("Stopped by user")
        stop_event.set()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        stop_event.set()
    finally:
        stop()
        try:
            if pwm_a is not None:
                pwm_a.stop()
            if pwm_b is not None:
                pwm_b.stop()
        except Exception as e:
            logger.error(f"Error stopping PWM: {e}")
        GPIO.cleanup()
        client_socket.close()
        face_mesh.close()
        logger.info("Application closed")

if __name__ == "__main__":
    main()