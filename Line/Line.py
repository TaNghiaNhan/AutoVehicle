import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.optimizers import Adam
from PIL import Image
import math
IMAGE_HEIGHT = 66
IMAGE_WIDTH = 200
IMAGE_CHANNELS = 3

model_path = "/model_tf218.h5"

def build_nvidia_model():
    inputs = layers.Input(shape=(IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_CHANNELS))
    x = layers.Lambda(lambda x: x)(inputs)
    x = layers.Conv2D(24, (5, 5), strides=(2, 2), activation='relu')(x)
    x = layers.Conv2D(36, (5, 5), strides=(2, 2), activation='relu')(x)
    x = layers.Conv2D(48, (5, 5), strides=(2, 2), activation='relu')(x)
    x = layers.Conv2D(64, (3, 3), activation='relu')(x)
    x = layers.Conv2D(64, (3, 3), activation='relu')(x)
    x = layers.Flatten()(x)
    x = layers.Dense(100, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(50, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(10, activation='relu')(x)
    outputs = layers.Dense(1)(x)
    model = Model(inputs=inputs, outputs=outputs)
    return model

def load_model_with_fallback(model_path):
    try:
        print("Attempting standard model loading...")
        model = tf.keras.models.load_model(model_path)
        return model
    except Exception as e:
        print(f"Standard loading failed: {e}")
        try:
            print("Attempting to load with compile=False...")
            model = tf.keras.models.load_model(model_path, compile=False)
            return model
        except Exception as e:
            print(f"Loading with compile=False failed: {e}")
            model = build_nvidia_model()
            optimizer = Adam(learning_rate=0.0001)
            model.compile(loss='mse', optimizer=optimizer)
            return model

# Preprocess image for prediction
def preprocess_image(image):
    img = Image.fromarray(image)
    img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT))
    img_array = np.array(img)
    img_array = img_array / 255.0 - 0.5
    return img_array

def visualize_prediction_on_frame(frame, steering_angle):
    steering_angle_degrees = steering_angle * (180.0 / np.pi)
    print(steering_angle_degrees)
    h, w = frame.shape[0], frame.shape[1]
    center_x, center_y = w // 2, h - 20
    length = min(h, w) // 3
    end_x = center_x + length * math.sin(steering_angle)
    end_y = center_y - length * math.cos(steering_angle)

    frame_with_prediction = frame.copy()
    cv2.line(frame_with_prediction, (center_x, center_y), (int(end_x), int(end_y)), (0, 0, 255), 4)
    cv2.circle(frame_with_prediction, (center_x, center_y), 5, (255, 0, 0), -1)
    cv2.putText(frame_with_prediction, f"Angle: {steering_angle_degrees:.2f} degrees", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    return frame_with_prediction

def predict_from_video(video_path, output_video_path):
    # Open video capture
    cap = cv2.VideoCapture(video_path)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (960, 640))

    model = load_model_with_fallback(model_path)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        img_array = preprocess_image(frame)

        steering_angle = model.predict(np.expand_dims(img_array, axis=0), verbose=0)[0][0]

        frame_with_prediction = visualize_prediction_on_frame(frame, steering_angle)

        frame_resized = cv2.resize(frame_with_prediction, (960, 640))

        out.write(frame_resized)

        cv2.imshow("Prediction", frame_resized)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

predict_from_video("D:/MyWorkSpace/PythonProject/TrainLaneDetection/Recording 2025-04-13 175257.mp4",
                   "D:/MyWorkSpace/PythonProject/TrainLaneDetection/output_video.mp4")