import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os
import serial
import time

ser = serial.Serial('/dev/cu.usbmodem101', 115200)
time.sleep(2)
#person is 76in out, camera is 36in tall and 90degrees

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), # Shoulders and arms
    (11, 23), (12, 24), (23, 24), # Torso / Hips
    (23, 25), (25, 27), (24, 26), (26, 28) # Legs
]

def draw_landmarks_on_image(rgb_image, detection_result):
    if not detection_result.pose_landmarks:
        return rgb_image

    annotated_image = np.copy(rgb_image)
    h, w, _ = annotated_image.shape
    pose_landmarks_list = detection_result.pose_landmarks

    for pose_landmarks in pose_landmarks_list:
        for connection in POSE_CONNECTIONS:
            start_idx, end_idx = connection
            start_lm = pose_landmarks[start_idx]
            end_lm = pose_landmarks[end_idx]
            
            if start_lm.visibility > 0.5 and end_lm.visibility > 0.5:
                start_point = (int(start_lm.x * w), int(start_lm.y * h))
                end_point = (int(end_lm.x * w), int(end_lm.y * h))
                cv2.line(annotated_image, start_point, end_point, (0, 255, 0), 2, cv2.LINE_AA)

        for lm in pose_landmarks:
            if lm.visibility > 0.5:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(annotated_image, (cx, cy), 5, (255, 0, 255), -1)

    return annotated_image


calibration_ready = False
calibrating_step = "Noone In Frame"
state = "standing"
capturing = True
cap = cv2.VideoCapture(0)

coordinates = (50, 80) 
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 2
color = (0, 255, 0)
thickness = 3
prevstate = state

base_options = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options = vision.PoseLandmarkerOptions(
    running_mode=vision.RunningMode.IMAGE,
    base_options=base_options,
    output_segmentation_masks=False,
    min_pose_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.PoseLandmarker.create_from_options(options)

while capturing:
    ret, frame = cap.read()
    cv2.imwrite("image.jpg", frame)

    image = mp.Image.create_from_file("image.jpg")

    detection_result = detector.detect(image)

    if detection_result.pose_landmarks:
        left_hip = detection_result.pose_landmarks[0][23]
        right_hip = detection_result.pose_landmarks[0][24]
        lh_norm_y = left_hip.y
        rh_norm_y = right_hip.y
        avg = (lh_norm_y+rh_norm_y)/2
        # if avg < 0.47:
        #     state = "Jumping"
        # elif avg < 0.545:
        #     state = "Standing"
        # else:
        #     state = "Squatting"


        if not calibration_ready:
            #print calibrating here,
            if avg < 0.48:
                calibrating_step = "Step Forward"
            elif avg > 0.52:
                pass
                calibrating_step = "Step Back"
            elif avg > 0.485 and avg < 0.515:
                calibration_ready = True
        else:
            #print the state here
            if avg < 0.44:
                state = "Jumping"
            elif avg < 0.6:
                state = "Standing"
            else:
                state = "Squatting"
        
        # print(f"Left Hip (ID 23) -> Y: {avg}\nState: {state}")

    if (prevstate != state):
        ser.write((state+"\n").encode('utf-8'))
        print(state)
        prevstate = state
    print(ser.read_all().decode('utf-8'))

    #just for like output
    raw_rgb_view = image.numpy_view()
    annotated_image_rgb = draw_landmarks_on_image(raw_rgb_view, detection_result)
    final_bgr_image = cv2.cvtColor(annotated_image_rgb, cv2.COLOR_RGB2BGR)
    if not calibration_ready:
        cv2.putText(final_bgr_image, f"Calibrating...{calibrating_step}", coordinates, font, font_scale, color, thickness)
    else:
        cv2.putText(final_bgr_image, f"{state}", coordinates, font, font_scale, color, thickness)
    cv2.imshow("Display Window", final_bgr_image)
    cv2.waitKey(1)
    os.remove("image.jpg")

cv2.destroyAllWindows()
cap.release()
ser.close()