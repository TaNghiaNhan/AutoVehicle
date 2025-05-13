import cv2
import numpy as np
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from time import sleep, time

# ======== GPIO Setup ========
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Motor A (right)
IN1 = 5
IN2 = 6
ENA = 13
# Motor B (left)
IN3 = 19
IN4 = 26
ENB = 12

GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

pwm_right = GPIO.PWM(ENA, 1000)
pwm_left = GPIO.PWM(ENB, 1000)
pwm_right.start(0)
pwm_left.start(0)

# ======== Motor Control Function ========
def set_motor_direction(in1, in2, pwm, speed):
    if speed > 0:
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
        pwm.ChangeDutyCycle(speed)
    else:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.LOW)
        pwm.ChangeDutyCycle(0)

# ======== Image Processing Functions ========
def canny(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    return cv2.Canny(blur, 15, 50)

def create_color_mask(image):
    bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([100, 100, 100])
    mask = cv2.inRange(bgr_image, lower_black, upper_black)
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    return mask

def region_of_interest(image):
    height = image.shape[0]
    width = image.shape[1]
    polygons = np.array([[(int(width * 0.1), height), (int(width * 0.9), height), (int(width * 0.5), int(height * 0.3))]])
    mask = np.zeros_like(image)
    if len(image.shape) == 2:
        cv2.fillPoly(mask, polygons, 255)
    else:
        cv2.fillPoly(mask, polygons, (255, 255, 255))
    return cv2.bitwise_and(image, mask)

def make_coordinates(image, line_parameters):
    try:
        slope, intercept = line_parameters
        y1 = image.shape[0]
        y2 = int(y1 * (3 / 5))
        x1 = int((y1 - intercept) / slope)
        x2 = int((y2 - intercept) / slope)
        if np.isnan(x1) or np.isnan(x2) or np.isinf(x1) or np.isinf(x2) or x1 < 0 or x1 >= image.shape[1] or x2 < 0 or x2 >= image.shape[1]:
            return None
        return np.array([x1, y1, x2, y2], dtype=np.int32)
    except (ValueError, ZeroDivisionError):
        return None

def get_best_line(image, lines):
    if lines is None or len(lines) == 0:
        return None, 0
    best_line = None
    max_length = 0
    for line in lines:
        x1, y1, x2, y2 = line.reshape(4)
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length > max_length:
            max_length = length
            best_line = line
    if best_line is not None:
        x1, y1, x2, y2 = best_line.reshape(4)
        if (abs(x2 - x1) < 1e-5):
            return None, 0
        parameters = np.polyfit((x1, x2), (y1, y2), 1)
        slope = parameters[0]
        return make_coordinates(image, parameters), slope
    return None, 0

def get_direction(line, slope):
    if line is None or abs(slope) >= 2.75:
        return 'S', 0
    if slope > 0:
        return 'R', slope
    elif slope < 0:
        return 'L', slope
    else:
        return 'S', slope

def control_motors(direction, slope):
    base_speed = 27
    alpha = 1.5
    if direction == 'S' or abs(slope) >= 2.75:
        left_speed = base_speed
        right_speed = base_speed
    else:
        if (abs(slope) <= 2.75):
            steer_ratio = min(abs(slope), 1.0)
            alpha = 1.5
        # else:
            # steer_ratio = min(0.3 / abs(slope), 1.0)
        print(f"Steer ratio: {steer_ratio}")
        if direction == 'R':
            left_speed = base_speed * (1 - steer_ratio * 0.4) + 30 * alpha
            right_speed = 0
        elif direction == 'L':
            left_speed = 0
            right_speed = base_speed * (1 - steer_ratio * 0.4) + 30 * alpha

    left_speed = max(0, min(100, left_speed))
    right_speed = max(0, min(100, right_speed))
    print(f"Left speed: {left_speed}%, Right speed: {right_speed}%")
    set_motor_direction(IN1, IN2, pwm_right, left_speed)
    set_motor_direction(IN3, IN4, pwm_left, right_speed)

def display_lines(image, line):
    line_image = np.zeros_like(image)
    if line is not None:
        x1, y1, x2, y2 = line.reshape(4)
        cv2.line(line_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 5)
    return line_image

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        color = param[y, x]
        print(f"Color at ({x}, {y}): {color}")

# ======== Main Loop ========
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (480, 320)}))
picam2.start()
sleep(2)

try:
    while True:
        start_time = time()
        
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        color_mask = create_color_mask(frame)
        canny_image = canny(frame)
        combined_image = cv2.bitwise_and(canny_image, color_mask)
        cropped_image = region_of_interest(combined_image)
        lines = cv2.HoughLinesP(cropped_image, 1, np.pi / 180, 5, np.array([]), minLineLength=10, maxLineGap=5)

        best_line, slope = get_best_line(frame, lines)
        line_image = display_lines(frame, best_line)
        combo_image = cv2.addWeighted(frame, 0.8, line_image, 1, 1)

        direction, slope = get_direction(frame, best_line, slope)
        control_motors(direction, slope)

        # Calculate FPS
        end_time = time()
        fps = 1 / (end_time - start_time)
        print(f"FPS: {fps:.2f}")

        # Display FPS on the image
        cv2.putText(combo_image, f'FPS: {fps:.2f}', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.putText(combo_image, f'Direction: {direction}', (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow('Original', frame)
        cv2.imshow('Color Mask', color_mask)
        cv2.imshow('Canny + ROI', cropped_image)
        cv2.imshow('Lane Detection + Steering', combo_image)

        cv2.namedWindow('Original')
        cv2.setMouseCallback('Original', mouse_callback, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pwm_right.stop()
    pwm_left.stop()
    GPIO.cleanup()
    picam2.stop()
    cv2.destroyAllWindows()
