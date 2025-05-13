import RPi.GPIO as GPIO
import time
import logging
import curses

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
    pwm_a = GPIO.PWM(ENA, 1000)
    pwm_b = GPIO.PWM(ENB, 1000)
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
    time.sleep(0.8)
    stop()
    logger.info("Moving forward")

def move_backward(speed=25):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "backward")
    time.sleep(0.9)
    stop()
    logger.info("Moving backward")

def turn_left(speed=100):
    set_motor("motor1", speed, "forward")
    set_motor("motor2", speed, "backward")
    time.sleep(0.34*2)
    stop()
    logger.info("Turning left")

def turn_right(speed=100):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "forward")
    time.sleep(0.22*2)
    stop()
    logger.info("Turning right")

def stop():
    set_motor("motor1", 0, "stop")
    set_motor("motor2", 0, "stop")
    logger.info("Stopped")

def main(stdscr):
    # Set up curses
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.timeout(50)

    logger.info("Keyboard control started. Use Arrow Keys: Up: Forward, Down: Backward, Left: Left, Right: Right, Space: Stop, Q: Quit")

    try:
        while True:
            try:
                key = stdscr.getch()
                if key == curses.KEY_UP:
                    move_forward()
                elif key == curses.KEY_DOWN:
                    move_backward()
                elif key == curses.KEY_LEFT:
                    turn_left()
                elif key == curses.KEY_RIGHT:
                    turn_right()
                elif key == ord(' '):
                    stop()
                elif key == ord('q') or key == ord('Q'):
                    logger.info("Program stopped by user")
                    break
            except curses.error:
                pass
            time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Program stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        stop()
        try:
            pwm_a.stop()
            pwm_b.stop()
        except Exception as e:
            logger.error(f"Error stopping PWM: {e}")
        GPIO.cleanup()
        logger.info("Cleanup completed")

if __name__ == "__main__":
    curses.wrapper(main)