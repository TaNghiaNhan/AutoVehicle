import RPi.GPIO as GPIO
import time
import logging
import numpy as np
import cv2
from tflite_runtime.interpreter import Interpreter
from picamera2 import Picamera2

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Resolution 320x240
frameWidth = 320
frameHeight = 240
threshold = 0.9
font = cv2.FONT_HERSHEY_SIMPLEX

windowName = "Traffic Sign Following Robot"

# ==================== CAMERA SETUP ====================
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (frameWidth, frameHeight)}))
picam2.start()
time.sleep(1)

# ==================== LOAD TFLITE MODEL ====================
interpreter = Interpreter(model_path=r"/home/f1/Code/model_trained.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# ==================== IMAGE PROCESSING ====================
def grayscale(img): return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
def equalize(img): return cv2.equalizeHist(img)
def preprocessing(img): return equalize(grayscale(img)) / 255.0

# ==================== CLASS LABELS ====================
def getClassName(classNo):
    classes = [
        'Speed Limit 20 km/h', 
        'Speed Limit 30 km/h', 
        'Speed Limit 50 km/h',
        'Speed Limit 60 km/h', 
        'Speed Limit 70 km/h', 
        'Speed Limit 80 km/h',
        'End of Speed Limit 80 km/h', 
        'Speed Limit 100 km/h', 
        'Speed Limit 120 km/h',
        'No passing', 
        'No passing > 3.5 tons', 
        'Right-of-way at the next intersection',
        'Priority road', 
        'Yield', 
        'Stop', 
        'No vehicles', 
        'Vehicles > 3.5 tons prohibited',
        'No entry', 
        'General caution', 
        'Dangerous curve to the left', 
        'Dangerous curve to the right',
        'Double curve', 
        'Bumpy road', 
        'Slippery road', 
        'Road narrows on the right',
        'Road work', 
        'Traffic signals', 
        'Pedestrians', 
        'Children crossing',
        'Bicycles crossing', 
        'Beware of ice/snow', 
        'Wild animals crossing',
        'End of all speed and passing limits', 
        'Turn right ahead', 
        'Turn left ahead',
        'Ahead only', 
        'Go straight or right', 
        'Go straight or left', 
        'Keep right',
        'Keep left', 
        'Roundabout mandatory', 
        'End of no passing', 
        'End of no passing > 3.5 tons'
    ]
    return classes[classNo] if 0 <= classNo < len(classes) else "Unknown"

# ==================== ROBOT CAR SETUP & CONTROL ====================
# Set up GPIO
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
    """Điều khiển động cơ với tốc độ và hướng cụ thể"""
    """Control the motor with specific speed and direction"""
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

def move_forward(speed=30, duration=None):
    set_motor("motor1", speed, "forward")
    set_motor("motor2", speed, "forward")
    logger.info(f"Moving forward at speed {speed}")
    if duration:
        time.sleep(duration)
        stop()

def move_backward(speed=20, duration=None):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "backward")
    logger.info(f"Moving backward at speed {speed}")
    if duration:
        time.sleep(duration)
        stop()

def turn_left(speed=65, duration=None):
    set_motor("motor1", speed, "forward")
    set_motor("motor2", speed, "backward")
    logger.info("Turning left")
    if duration:
        time.sleep(duration)
        stop()

def turn_right(speed=65, duration=None):
    set_motor("motor1", speed, "backward")
    set_motor("motor2", speed, "forward")
    logger.info("Turning right")
    if duration:
        time.sleep(duration)
        stop()

def make_u_turn(speed=50):
    logger.info("Making U-turn")
    turn_right(speed, 0.00001)
    stop()

def stop():
    set_motor("motor1", 0, "stop")
    set_motor("motor2", 0, "stop")
    logger.info("Stopped")

# ==================== TRAFFIC SIGN REACTION FUNCTIONS ====================
def react_to_traffic_sign(class_name, probability):
    """React to detected traffic signs"""
    logger.info(f"Detected: {class_name} ({probability*100:.2f}%)")
    
    # Speed limit signs - adjust speed based on limit
    if "Speed Limit" in class_name:
        try:
            speed_limit = int(class_name.split()[2])  # Extract the number
            # Scale the speed limit to a reasonable motor speed (0-100)
            # Assuming max speed limit 120km/h = 100% motor speed
            motor_speed = int(min(40, 100))
            logger.info(f"Adjusting speed to {motor_speed}% according to {speed_limit} km/h limit")
            move_forward(speed=motor_speed)
        except:
            logger.error(f"Could not parse speed limit from: {class_name}")
            move_forward(speed=20)
    
    # Direction signs
    elif "Turn right ahead" in class_name:
        stop()
        time.sleep(0.5)
        turn_right(duration=0.5)
        move_forward()
    
    elif "Turn left ahead" in class_name:
        stop()
        time.sleep(0.5)
        turn_left(100, duration=0.44)
        move_forward()
    
    elif "Roundabout mandatory" in class_name:
        stop()
        time.sleep(0.5)
        turn_left(100, duration=0.22*2)
        move_forward()

    else: 
        move_forward(speed=20)

# ==================== CREATE WINDOW ====================
cv2.namedWindow(windowName, cv2.WINDOW_NORMAL)
cv2.resizeWindow(windowName, frameWidth, frameHeight)

# ==================== MAIN FUNCTION ====================
def main():
    last_sign_time = 0
    sign_cooldown = 2  # seconds between sign reactions to avoid rapid switching
    default_action_interval = 1.0  # seconds between default forward movements
    last_default_action = 0
    current_sign = None
    
    try:
        # Start moving forward by default
        move_forward(speed=30)
        
        while True:
            # Image from camera
            imgOriginal = picam2.capture_array()

            # Define the region of interest (ROI)
            roi_x, roi_y = 180, 10
            roi_w, roi_h = 100, 100 
            roi = imgOriginal[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]

            # Preprocessing the image for classification
            img = cv2.resize(roi, (32, 32))
            img = preprocessing(img)
            img_input = img.reshape(1, 32, 32, 1).astype(np.float32)

            interpreter.set_tensor(input_details[0]['index'], img_input)
            interpreter.invoke()

            # Taking the results
            predictions = interpreter.get_tensor(output_details[0]['index'])
            classIndex = int(np.argmax(predictions))
            probabilityValue = np.max(predictions)

            # Display the results
            if probabilityValue > threshold:
                className = getClassName(classIndex)
                cv2.putText(imgOriginal, f"{className}", (roi_x, roi_y - 10), font, 0.7, (0, 0, 255), 2)
                cv2.putText(imgOriginal, f"{round(probabilityValue * 100, 2)}%", (roi_x, roi_y + roi_h + 25), font, 0.6, (0, 255, 0), 2)
                
                # React to sign if it's a new sign or cooldown has passed
                current_time = time.time()
                if (className != current_sign or (current_time - last_sign_time) > sign_cooldown):
                    current_sign = className
                    last_sign_time = current_time
                    react_to_traffic_sign(className, probabilityValue)
            else:
                # If no sign is detected for a while, continue moving forward
                current_time = time.time()
                if current_time - last_default_action > default_action_interval:
                    move_forward(speed=30)
                    last_default_action = current_time

            cv2.rectangle(imgOriginal, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (255, 0, 0), 2)
            cv2.putText(imgOriginal, "ROI", (roi_x, roi_y - 30), font, 0.6, (255, 0, 0), 2)

            cv2.imshow(windowName, imgOriginal)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        stop()
        try:
            pwm_a.stop()
            pwm_b.stop()
        except Exception as e:
            logger.error(f"Error stopping PWM: {e}")
        GPIO.cleanup()
        cv2.destroyAllWindows()
        picam2.stop()
        logger.info("Application closed")

if __name__ == "__main__":
    main()