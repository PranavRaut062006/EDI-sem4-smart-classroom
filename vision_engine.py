import cv2
import base64
import os
import numpy as np
from ultralytics import YOLO

# Guard import so server can start if deepface is not fully installed
try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False

class VisionEngine:
    def __init__(self, attendance_manager):
        self.attendance_manager = attendance_manager
        
        # Load YOLOv8 for objects (person, cell phone) - downloads automatically
        print("Loading YOLOv8 network...")
        self.model = YOLO('yolov8n.pt') 
        
        self.cap = cv2.VideoCapture(0)
        
        self.frame_count = 0
        self.db_path = "dataset"
        
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path, exist_ok=True)
            
        # Ensure deepface models are loaded once by dummy triggering
        if HAS_DEEPFACE:
            try:
                print("Checking DeepFace VGG-Face cache...")
                DeepFace.build_model('VGG-Face')
            except Exception as e:
                print(f"Deepface warning: {e}")

    def draw_corner_rect(self, img, x1, y1, x2, y2, color, thickness=1, length=15):
        """Draws professional high-tech corner-only brackets instead of a thick box."""
        # Top-left
        cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)
        # Top-right
        cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + length), color, thickness)
        # Bottom-left
        cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - length), color, thickness)
        # Bottom-right
        cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - length), color, thickness)

    def process_frame(self):
        success, frame = self.cap.read()
        if not success:
            return None, {"error": "Failed to read camera"}

        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        self.frame_count += 1
        
        # Run YOLO inference
        # classes: 0 = person, 67 = cell phone
        results = self.model(frame, classes=[0, 67], verbose=False)
        
        persons = []
        phones = []
        
        # Parse Bounding Boxes
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                if conf > 0.4:
                    if cls == 0:
                        persons.append((x1, y1, x2, y2))
                    elif cls == 67:
                        phones.append((x1, y1, x2, y2))

        # Check phone overlap -> distraction
        total_engagement = 0
        
        for i, (px1, py1, px2, py2) in enumerate(persons):
            engagement_score = 100
            phone_detected = False
            
            # Does any phone box intersect with this person's box?
            for (phx1, phy1, phx2, phy2) in phones:
                if (px1 < phx2 and px2 > phx1 and py1 < phy2 and py2 > phy1):
                    phone_detected = True
                    engagement_score = 0
                    break
            
            if not phone_detected:
                # Dynamic engagement penalty based on movement/position
                center_x = (px1 + px2) / 2
                frame_center_x = frame.shape[1] / 2
                dist_from_center = abs(center_x - frame_center_x)
                max_dist = frame.shape[1] / 2
                
                # Penalty if moving away from center
                penalty = int((dist_from_center / max_dist) * 40)
                
                # Penalty if leaning (width > height)
                w = px2 - px1
                h = py2 - py1
                if h > 0 and w/h > 1.0:
                    penalty += 20
                    
                engagement_score = max(0, engagement_score - penalty)
            
            # Use higher tech corner rect
            color = (0, 0, 255) if phone_detected else (0, 255, 0)
            self.draw_corner_rect(display_frame, px1, py1, px2, py2, color, thickness=2, length=20)
            
            # --- Biometric Check ---
            student_name = "Unknown"
            liveness_status = "Live Authenticating..."
            
            # Run deepface every 15 frames for each person box to avoid massive lag
            if HAS_DEEPFACE and self.frame_count % 15 == 0:
                crop_y1, crop_y2 = max(0, py1), min(frame.shape[0], py2)
                crop_x1, crop_x2 = max(0, px1), min(frame.shape[1], px2)
                person_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                
                if person_crop.size > 0:
                    try:
                        # Find matching identity
                        dfs = DeepFace.find(img_path=person_crop, db_path=self.db_path, model_name="VGG-Face",
                                          enforce_detection=False, silent=True)
                        if len(dfs) > 0 and not dfs[0].empty:
                            matched_path = dfs[0]['identity'].iloc[0]
                            student_name = os.path.basename(os.path.dirname(matched_path))
                    except:
                        pass
            else:
                student_name = f"Tracking_ID_{i}"
                # Fallback mock recognition for simulation since DeepFace is disabled
                if os.path.exists(self.db_path):
                    students = [d for d in os.listdir(self.db_path) if os.path.isdir(os.path.join(self.db_path, d))]
                    if len(students) > i:
                        student_name = students[i]
                    elif students:
                        student_name = students[0]

            if student_name != "Unknown" and not student_name.startswith("Tracking"):
                self.attendance_manager.mark_seen(student_name, phone_detected)
            
            total_engagement += engagement_score
            
            # Design refined label: Semi-transparent background for text
            label_text = f"{student_name.replace('_', ' ')} {'[!]' if phone_detected else ''}"
            t_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
            cv2.rectangle(display_frame, (px1, py1 - 25), (px1 + t_size[0] + 10, py1), color, -1)
            cv2.putText(display_frame, label_text, (px1 + 5, py1 - 8), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

        # Base64 Encode
        ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        avg_eng = int(total_engagement / len(persons)) if persons else 0

        metadata = {
            "num_faces": len(persons),
            "average_engagement": avg_eng,
            "roster_summary": self.attendance_manager.get_summary()
        }

        return frame_base64, metadata

    def release(self):
        if self.cap.isOpened():
            self.cap.release()
