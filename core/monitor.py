import base64
import time
from collections import deque
import cv2
import numpy as np
import mediapipe as mp

# Try loading YOLOv8 for phone detection. If it fails, degrade gracefully.
try:
    from ultralytics import YOLO
    # Load YOLOv8 nano model (pre-trained on COCO, class 67 is cell phone)
    yolo_model = YOLO('yolov8n.pt')
except Exception as e:
    print("Warning: Failed to load YOLOv8 model. Mobile phone detection will be disabled:", e)
    yolo_model = None


class DrowsinessMonitor:
    def __init__(self):
        # Settings
        self.ear_thresh = 0.22  # Eye Aspect Ratio threshold
        self.mar_thresh = 0.50  # Mouth Aspect Ratio threshold
        self.distraction_yaw_thresh = 20.0  # Yaw threshold in degrees
        self.distraction_pitch_thresh = 15.0  # Pitch threshold in degrees
        
        # State
        self.is_running = True
        self.fatigue_score = 0
        self.start_time = time.time()
        
        # Sliding windows for smoothing (30 frames ~ 2-3 seconds)
        self.ear_history = deque(maxlen=30)
        self.mar_history = deque(maxlen=30)
        
        # Sliding windows for head pose smoothing
        self.yaw_history = deque(maxlen=15)
        self.pitch_history = deque(maxlen=15)
        self.roll_history = deque(maxlen=15)
        
        # Calibration variables (Auto-calibrates to first 15 frames of straight-looking pose)
        self.yaw_offset = 0.0
        self.pitch_offset = 0.0
        self.roll_offset = 0.0
        self.calibrate_frames = 15
        self.yaw_accum = []
        self.pitch_accum = []
        self.roll_accum = []
        
        # Performance optimization: throttle object detection to once every 6 frames
        self.frame_counter = 0
        self.last_phone_detected = False
        self.last_phone_box = None
        
        # MediaPipe Face Mesh Setup
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Alert frame counters
        self.eyes_closed_frames = 0
        self.yawn_frames = 0
        self.distracted_frames = 0
        self.phone_detected_frames = 0
        
        # Frame thresholds (assumes ~12 FPS stream)
        self.drowsy_frame_limit = 15     # ~1.2 seconds of closed eyes
        self.yawn_frame_limit = 15       # ~1.2 seconds of yawning
        self.distracted_frame_limit = 15 # ~1.2 seconds of looking away
        
        # 3D Model points for Head Pose solvePnP
        # Coordinates in world space (mm) centered around nose tip
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye corner (user's right, screen left)
            (225.0, 170.0, -135.0),      # Right eye corner (user's left, screen right)
            (-150.0, -150.0, -125.0),    # Left mouth corner (screen left)
            (150.0, -150.0, -125.0)      # Right mouth corner (screen right)
        ], dtype=np.float32)

    def start(self):
        self.is_running = True
        print("Drowsiness Monitor started.")

    def stop(self):
        self.is_running = False
        print("Drowsiness Monitor stopped.")

    def reset(self):
        self.fatigue_score = 0
        self.eyes_closed_frames = 0
        self.yawn_frames = 0
        self.distracted_frames = 0
        self.phone_detected_frames = 0
        self.ear_history.clear()
        self.mar_history.clear()
        self.yaw_history.clear()
        self.pitch_history.clear()
        self.roll_history.clear()
        
        # Re-trigger calibration
        self.yaw_offset = 0.0
        self.pitch_offset = 0.0
        self.roll_offset = 0.0
        self.calibrate_frames = 15
        self.yaw_accum = []
        self.pitch_accum = []
        self.roll_accum = []
        print("Drowsiness Monitor reset. Recalibrating pose offsets...")

    def update_settings(self, ear_thresh, mar_thresh):
        try:
            self.ear_thresh = float(ear_thresh)
            self.mar_thresh = float(mar_thresh)
            print(f"Settings updated: EAR Threshold = {self.ear_thresh}, MAR Threshold = {self.mar_thresh}")
        except ValueError:
            print("Invalid threshold values provided.")

    def _calculate_ear(self, landmarks, w, h):
        """Calculate Eye Aspect Ratio (EAR)"""
        # Right eye indices (screen left/user's right)
        # horizontal: 33, 133. vertical: 160-153, 159-145
        r_p1 = np.array([landmarks[33].x * w, landmarks[33].y * h])
        r_p2 = np.array([landmarks[160].x * w, landmarks[160].y * h])
        r_p3 = np.array([landmarks[159].x * w, landmarks[159].y * h])
        r_p4 = np.array([landmarks[133].x * w, landmarks[133].y * h])
        r_p5 = np.array([landmarks[145].x * w, landmarks[145].y * h])
        r_p6 = np.array([landmarks[153].x * w, landmarks[153].y * h])
        
        # Left eye indices (screen right/user's left)
        # horizontal: 362, 263. vertical: 385-380, 386-374
        l_p1 = np.array([landmarks[362].x * w, landmarks[362].y * h])
        l_p2 = np.array([landmarks[385].x * w, landmarks[385].y * h])
        l_p3 = np.array([landmarks[386].x * w, landmarks[386].y * h])
        l_p4 = np.array([landmarks[263].x * w, landmarks[263].y * h])
        l_p5 = np.array([landmarks[374].x * w, landmarks[374].y * h])
        l_p6 = np.array([landmarks[380].x * w, landmarks[380].y * h])
        
        # EAR calculation
        def ear_for_eye(p1, p2, p3, p4, p5, p6):
            v1 = np.linalg.norm(p2 - p6)
            v2 = np.linalg.norm(p3 - p5)
            h = np.linalg.norm(p1 - p4)
            if h < 1e-6:
                return 0.0
            return (v1 + v2) / (2.0 * h)
            
        r_ear = ear_for_eye(r_p1, r_p2, r_p3, r_p4, r_p5, r_p6)
        l_ear = ear_for_eye(l_p1, l_p2, l_p3, l_p4, l_p5, l_p6)
        
        return (r_ear + l_ear) / 2.0

    def _calculate_mar(self, landmarks, w, h):
        """Calculate Mouth Aspect Ratio (MAR)"""
        # Outer lips horizontal: 78, 308
        # Vertical inner lip points: 13-14 (midpoint), 82-87 (left), 312-317 (right)
        p1 = np.array([landmarks[78].x * w, landmarks[78].y * h])
        p2 = np.array([landmarks[82].x * w, landmarks[82].y * h])
        p3 = np.array([landmarks[13].x * w, landmarks[13].y * h])
        p4 = np.array([landmarks[312].x * w, landmarks[312].y * h])
        p5 = np.array([landmarks[308].x * w, landmarks[308].y * h])
        p6 = np.array([landmarks[317].x * w, landmarks[317].y * h])
        p7 = np.array([landmarks[14].x * w, landmarks[14].y * h])
        p8 = np.array([landmarks[87].x * w, landmarks[87].y * h])
        
        v1 = np.linalg.norm(p2 - p8)
        v2 = np.linalg.norm(p3 - p7)
        v3 = np.linalg.norm(p4 - p6)
        h_dist = np.linalg.norm(p1 - p5)
        
        if h_dist < 1e-6:
            return 0.0
        return (v1 + v2 + v3) / (3.0 * h_dist)

    def _estimate_head_pose(self, landmarks, w, h):
        """Estimate Head Pose (Yaw, Pitch, Roll) using solvePnP"""
        # Map facial landmarks to our model points
        # 1: Nose, 152: Chin, 33: Screen Left Eye corner, 263: Screen Right Eye corner,
        # 61: Screen Left Mouth corner, 291: Screen Right Mouth corner
        image_points = np.array([
            (landmarks[4].x * w, landmarks[4].y * h),       # Nose tip (landmark 4)
            (landmarks[152].x * w, landmarks[152].y * h),   # Chin (landmark 152)
            (landmarks[33].x * w, landmarks[33].y * h),     # Left eye corner (landmark 33)
            (landmarks[263].x * w, landmarks[263].y * h),   # Right eye corner (landmark 263)
            (landmarks[61].x * w, landmarks[61].y * h),     # Left mouth corner (landmark 61)
            (landmarks[291].x * w, landmarks[291].y * h)    # Right mouth corner (landmark 291)
        ], dtype=np.float32)
        
        # Camera internal parameters
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float32)
        
        dist_coeffs = np.zeros((4, 1), dtype=np.float32) # Assuming no lens distortion
        
        success, rvec, tvec = cv2.solvePnP(
            self.model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return 0.0, 0.0, 0.0, None, None
            
        # Rodrigues formula to get Rotation Matrix
        rmat, _ = cv2.Rodrigues(rvec)
        
        # Calculate Euler angles (Yaw, Pitch, Roll)
        sy = np.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
        singular = sy < 1e-6
        
        if not singular:
            pitch = np.arctan2(rmat[2, 1], rmat[2, 2])
            yaw = np.arctan2(-rmat[2, 0], sy)
            roll = np.arctan2(rmat[1, 0], rmat[0, 0])
        else:
            pitch = np.arctan2(-rmat[1, 2], rmat[1, 1])
            yaw = np.arctan2(-rmat[2, 0], sy)
            roll = 0.0
            
        # Convert to degrees
        pitch = np.degrees(pitch)
        yaw = np.degrees(yaw)
        roll = np.degrees(roll)
        
        return yaw, pitch, roll, camera_matrix, dist_coeffs

    def process_client_frame(self, base64_image):
        """Decode client frame, perform ML analysis, annotate frame, and encode back to base64"""
        if not self.is_running:
            return None, {}
            
        try:
            # 1. Decode base64 frame
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            img_data = base64.b64decode(base64_image)
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return None, {}
                
            h, w, c = frame.shape
            
            # Initialize metrics
            ear = 0.0
            mar = 0.0
            yaw, pitch, roll = 0.0, 0.0, 0.0
            phone_detected = False
            
            drowsy_alert = False
            yawning_alert = False
            distraction_alert = False
            
            # 2. YOLOv8 Mobile Phone Detection (run every 6 frames to save CPU, ~twice a second)
            self.frame_counter += 1
            if yolo_model is not None:
                if self.frame_counter % 6 == 0 or self.last_phone_box is None:
                    self.last_phone_detected = False
                    self.last_phone_box = None
                    results = yolo_model(frame, verbose=False)
                    for r in results:
                        boxes = r.boxes
                        for box in boxes:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            # Class 67 in COCO dataset is 'cell phone'
                            if cls == 67 and conf > 0.45:
                                self.last_phone_detected = True
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                self.last_phone_box = (x1, y1, x2, y2, conf)
                                break  # Limit to one phone detection to keep inference overhead low
                
                phone_detected = self.last_phone_detected
                if phone_detected and self.last_phone_box is not None:
                    x1, y1, x2, y2, conf = self.last_phone_box
                    # Draw bounding box for cell phone
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 77, 255), 3)
                    cv2.putText(frame, f"CELL PHONE ({conf*100:.0f}%)", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 77, 255), 2)
            
            # 3. MediaPipe Face Landmarks
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            face_detected = False
            if results.multi_face_landmarks:
                face_detected = True
                landmarks = results.multi_face_landmarks[0].landmark
                
                # Calculate face bounding box from landmarks (min/max coords)
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                # Convert to pixel coordinates
                x1, y1 = int(x_min * w), int(y_min * h)
                x2, y2 = int(x_max * w), int(y_max * h)
                
                # Add padding
                padding_x = int((x2 - x1) * 0.08)
                padding_y = int((y2 - y1) * 0.1)
                x1 = max(0, x1 - padding_x)
                y1 = max(0, y1 - padding_y)
                x2 = min(w, x2 + padding_x)
                y2 = min(h, y2 + padding_y)
                
                # Draw a sleek bounding box around the face (Neon Cyan)
                box_color = (0, 242, 254)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                
                # Add a driver tracking tag at the top of the box
                cv2.rectangle(frame, (x1 - 1, y1 - 22), (x1 + 80, y1), box_color, -1)
                cv2.putText(frame, "DRIVER", (x1 + 6, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
                # EAR & MAR Calculations
                ear = self._calculate_ear(landmarks, w, h)
                mar = self._calculate_mar(landmarks, w, h)
                
                self.ear_history.append(ear)
                self.mar_history.append(mar)
                
                # Smooth metrics using rolling average
                smoothed_ear = sum(self.ear_history) / len(self.ear_history)
                smoothed_mar = sum(self.mar_history) / len(self.mar_history)
                
                # Head Pose Estimation
                raw_yaw, raw_pitch, raw_roll, cam_matrix, dist_coeffs = self._estimate_head_pose(landmarks, w, h)
                
                # Perform auto-calibration
                if self.calibrate_frames > 0:
                    self.yaw_accum.append(raw_yaw)
                    self.pitch_accum.append(raw_pitch)
                    self.roll_accum.append(raw_roll)
                    self.calibrate_frames -= 1
                    if self.calibrate_frames == 0:
                        self.yaw_offset = sum(self.yaw_accum) / len(self.yaw_accum)
                        self.pitch_offset = sum(self.pitch_accum) / len(self.pitch_accum)
                        self.roll_offset = sum(self.roll_accum) / len(self.roll_accum)
                        print(f"Calibration finished. Yaw Offset: {self.yaw_offset:.2f}, Pitch Offset: {self.pitch_offset:.2f}")
                
                # Subtract calibration offset
                calibrated_yaw = raw_yaw - self.yaw_offset
                calibrated_pitch = raw_pitch - self.pitch_offset
                calibrated_roll = raw_roll - self.roll_offset
                
                # Smooth the calibrated pose angles
                self.yaw_history.append(calibrated_yaw)
                self.pitch_history.append(calibrated_pitch)
                self.roll_history.append(calibrated_roll)
                
                yaw = sum(self.yaw_history) / len(self.yaw_history)
                pitch = sum(self.pitch_history) / len(self.pitch_history)
                roll = sum(self.roll_history) / len(self.roll_history)
                
                # State checking & frame counting
                # A. Drowsiness (EAR < threshold)
                if smoothed_ear < self.ear_thresh:
                    self.eyes_closed_frames += 1
                else:
                    self.eyes_closed_frames = 0
                    
                if self.eyes_closed_frames >= self.drowsy_frame_limit:
                    drowsy_alert = True
                    
                # B. Yawning (MAR > threshold)
                if smoothed_mar > self.mar_thresh:
                    self.yawn_frames += 1
                else:
                    self.yawn_frames = 0
                    
                if self.yawn_frames >= self.yawn_frame_limit:
                    yawning_alert = True
                    
                # C. Head Pose Distraction (Yaw/Pitch out of range)
                is_looking_away = abs(yaw) > self.distraction_yaw_thresh or abs(pitch) > self.distraction_pitch_thresh
                if is_looking_away:
                    self.distracted_frames += 1
                else:
                    self.distracted_frames = 0
                    
                if self.distracted_frames >= self.distracted_frame_limit:
                    distraction_alert = True
                    
                # Visual Landmark Overlays for Alerts
                # Highlight nose tip (center of pose)
                nose = landmarks[1]
                cv2.circle(frame, (int(nose.x * w), int(nose.y * h)), 5, (0, 242, 254), -1)
                
            else:
                # No face detected - reset tracking frames
                self.eyes_closed_frames = 0
                self.yawn_frames = 0
                self.distracted_frames = 0
                
            # Phone detection counting
            if phone_detected:
                self.phone_detected_frames += 1
            else:
                self.phone_detected_frames = 0
                
            phone_alert = self.phone_detected_frames >= 5
            
            # 4. Calculate Fatigue Score (0 - 100)
            # Increase if alert states are active, slowly decrease if normal
            fatigue_increment = 0
            if drowsy_alert:
                fatigue_increment += 4
            if yawning_alert:
                fatigue_increment += 1
            if distraction_alert:
                fatigue_increment += 2
            if phone_alert:
                fatigue_increment += 3
                
            if fatigue_increment > 0:
                self.fatigue_score = min(100, self.fatigue_score + fatigue_increment)
            else:
                # Decay fatigue score slowly if everything is fine
                self.fatigue_score = max(0, self.fatigue_score - 0.2)
                
            # Define status message
            status_message = "Active"
            active_color = (0, 242, 254)  # Neon Cyan
            
            if phone_alert:
                status_message = "PHONE DETECTED!"
                active_color = (0, 77, 255)  # Bright Orange/Red
            elif drowsy_alert:
                status_message = "DROWSINESS DETECTED!"
                active_color = (0, 0, 255)  # Crimson Red
            elif distraction_alert:
                status_message = "DISTRACTED: LOOKING AWAY"
                active_color = (0, 159, 255)  # Amber
            elif yawning_alert:
                status_message = "YAWNING DETECTED"
                active_color = (255, 159, 67)  # Yellow
            elif not face_detected:
                status_message = "FACE NOT DETECTED"
                active_color = (128, 128, 128)  # Gray
                
            # 5. Overlays on the image (for debug/direct stream view)
            # Draw Status bar in the top center
            cv2.rectangle(frame, (0, 0), (w, 45), (15, 15, 18), -1)
            cv2.putText(frame, f"STATUS: {status_message}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, active_color, 2)
            cv2.putText(frame, f"FATIGUE: {int(self.fatigue_score)}%", (w - 180, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Encode frame back to base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            annotated_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
            
            # Build statistics payload
            stats = {
                'face_detected': face_detected,
                'ear': round(float(ear), 4),
                'mar': round(float(mar), 4),
                'ear_thresh': self.ear_thresh,
                'mar_thresh': self.mar_thresh,
                'head_yaw': round(float(yaw), 2),
                'head_pitch': round(float(pitch), 2),
                'head_roll': round(float(roll), 2),
                'drowsy': drowsy_alert,
                'yawning': yawning_alert,
                'distracted': distraction_alert,
                'phone_detected': phone_detected,
                'phone_alert': phone_alert,
                'fatigue_score': int(self.fatigue_score),
                'status_message': status_message
            }
            
            return annotated_base64, stats
            
        except Exception as e:
            print("Error processing client frame:", e)
            import traceback
            traceback.print_exc()
            return None, {}
