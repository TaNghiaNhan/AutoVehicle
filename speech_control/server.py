import RPi.GPIO as GPIO
import socket
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# MotorA (right)
IN1 = 5
IN2 = 6
ENA = 13
# MotorB (left)
IN3 = 19
IN4 = 26
ENB = 12

GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

try:
    pwm_a = GPIO.PWM(ENA, 100)
    pwm_b = GPIO.PWM(ENB, 100)
    pwm_a.start(0)
    pwm_b.start(0)
except Exception as e:
    logger.error(f"Error initializing PWM: {e}")
    GPIO.cleanup()
    exit(1)

def set_motor(motor, speed, direction):
    """Control motor with specific speed and direction"""
    speed = max(min(speed, 100), 0)
    if motor == "motor1":
        pwm = pwm_a
        in1, in2 = IN1, IN2
    elif motor == "motor2":
        pwm = pwm_b
        in1, in2 = IN3, IN4
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

def move_forward(speed=25):
    set_motor("motor1", speed, "forward")
    set_motor("motor2", speed, "forward")
    time.sleep(1)
    stop()
    logger.info("Moving forward")

def move_backward(speed=25):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "backward")
    time.sleep(1)
    stop()
    logger.info("Moving backward")

def turn_left(speed=60):
    set_motor("motor1", speed, "forward")
    set_motor("motor2", speed, "backward")
    time.sleep(0.5)
    stop()
    logger.info("Turning left")

def turn_right(speed=60):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "forward")
    time.sleep(0.5)
    stop()
    logger.info("Turning right")

def stop():
    set_motor("motor1", 0, "stop")
    set_motor("motor2", 0, "stop")
    logger.info("Stopped")

def main():
    HOST = '0.0.0.0'
    PORT = 12345
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    server_socket.settimeout(1.0)

    logger.info(f"Server UDP running at {HOST}:{PORT}...")
    logger.info("Send commands: forward, backward, left, right, stop, quit")

    try:
        while True:
            try:
                data, addr = server_socket.recvfrom(1024)
                command = data.decode('utf-8').strip().lower()
                logger.info(f"Receive from {addr}: {command}")

                if command == "forward":
                    move_forward()
                elif command == "backward":
                    move_backward()
                elif command == "left":
                    turn_left()
                elif command == "right":
                    turn_right()
                elif command == "stop":
                    stop()
                elif command == "quit":
                    logger.info("Program stopped by client")
                    break
                else:
                    logger.warning(f"Invalid commands: {command}")

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error processing command: {e}")

    except KeyboardInterrupt:
        logger.info("Program stopped by user")
    finally:
        stop()
        try:
            pwm_a.stop()
            pwm_b.stop()
        except Exception as e:
            logger.error(f"Error stopping PWM: {e}")
        server_socket.close()
        GPIO.cleanup()
        logger.info("Cleanup completed")

if __name__ == "__main__":
    main()