"""
Smart Classroom — Vision Engine
YOLOv8 for person/phone detection + OpenCV-based face recognition.
Uses Haar cascade for face detection + histogram comparison for matching.
Runs on laptop webcam (index 0).
"""

import cv2
import base64
import os
import numpy as np
import logging
import pickle

logger = logging.getLogger(__name__)

# ── Load YOLOv8 ──────────────────────────────────────────────────────────────
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning("ultralytics not installed. YOLO detection unavailable.")

# Path to dataset (relative to project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset")
YOLO_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolov8n.pt")

# Haar cascade for face detection
HAAR_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


class FaceDB:
    """
    Simple face database using OpenCV histogram comparison.
    Stores face embeddings as color histograms of detected face regions.
    Works on any Python version without dlib/TensorFlow.
    """

    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        self.known_faces = {}  # name -> list of face histograms
        self._orb = cv2.ORB_create(nfeatures=500)
        self.reload()

    def _compute_face_descriptor(self, face_img):
        """Compute a multi-feature descriptor for a face image with spatial grid."""
        face_resized = cv2.resize(face_img, (128, 128))
        gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Compute gradients for the whole image
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)
        direction = np.arctan2(sobely, sobelx)
        
        hsv = cv2.cvtColor(face_resized, cv2.COLOR_BGR2HSV)
        
        grid_size = 4
        cell_size = 128 // grid_size
        
        descriptors = []
        for i in range(grid_size):
            for j in range(grid_size):
                y_start = i * cell_size
                y_end = (i + 1) * cell_size
                x_start = j * cell_size
                x_end = (j + 1) * cell_size
                
                # Extract cell
                hsv_cell = hsv[y_start:y_end, x_start:x_end]
                mag_cell = magnitude[y_start:y_end, x_start:x_end]
                dir_cell = direction[y_start:y_end, x_start:x_end]
                
                # Histograms for cell
                hist_h = cv2.calcHist([hsv_cell], [0], None, [16], [0, 180])
                hist_s = cv2.calcHist([hsv_cell], [1], None, [16], [0, 256])
                mag_hist = cv2.calcHist([mag_cell.astype(np.float32)], [0], None, [16], [0, 256])
                dir_hist = cv2.calcHist([((dir_cell + np.pi) / (2 * np.pi) * 255).astype(np.float32)],
                                        [0], None, [16], [0, 256])
                
                cv2.normalize(hist_h, hist_h)
                cv2.normalize(hist_s, hist_s)
                cv2.normalize(mag_hist, mag_hist)
                cv2.normalize(dir_hist, dir_hist)
                
                descriptors.extend([hist_h.flatten(), hist_s.flatten(), mag_hist.flatten(), dir_hist.flatten()])
                
        descriptor = np.concatenate(descriptors)
        return descriptor

    def reload(self):
        """Load all student faces from dataset directory."""
        self.known_faces = {}

        if not os.path.exists(self.dataset_path):
            return

        for student_name in os.listdir(self.dataset_path):
            student_dir = os.path.join(self.dataset_path, student_name)
            if not os.path.isdir(student_dir):
                continue

            face_img_path = os.path.join(student_dir, "face_anchor.jpg")
            if not os.path.exists(face_img_path):
                continue

            img = cv2.imread(face_img_path)
            if img is None:
                continue

            # Try to detect face in the image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

            if len(faces) > 0:
                # Use the largest detected face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_crop = img[y:y + h, x:x + w]
            else:
                # Use center crop if no face detected
                h, w = img.shape[:2]
                cx, cy = w // 2, h // 2
                size = min(h, w) // 2
                face_crop = img[max(0, cy - size):cy + size, max(0, cx - size):cx + size]

            if face_crop.size > 0:
                descriptor = self._compute_face_descriptor(face_crop)
                self.known_faces[student_name] = descriptor
                logger.info("Loaded face for: %s", student_name)

        logger.info("FaceDB loaded %d students", len(self.known_faces))

    def recognize(self, face_crop) -> tuple:
        """
        Match a face crop against known faces.
        Returns (name, confidence) or (None, 0).
        """
        if not self.known_faces or face_crop.size == 0:
            return None, 0

        descriptor = self._compute_face_descriptor(face_crop)

        best_name = None
        best_score = -1

        for name, known_desc in self.known_faces.items():
            # Correlation comparison (higher = better match)
            score = np.dot(descriptor, known_desc) / (
                np.linalg.norm(descriptor) * np.linalg.norm(known_desc) + 1e-8
            )
            if score > best_score:
                best_score = score
                best_name = name

        # Threshold for positive match
        if best_score > 0.75:
            return best_name, best_score

        return None, best_score


class VisionEngine:
    def __init__(self, attendance_manager):
        self.attendance_manager = attendance_manager
        self.frame_count = 0
        self.cap = None
        self._started = False

        # YOLO model
        self.yolo_model = None
        if HAS_YOLO:
            model_path = YOLO_MODEL_PATH if os.path.exists(YOLO_MODEL_PATH) else "yolov8n.pt"
            logger.info("Loading YOLOv8 from %s ...", model_path)
            self.yolo_model = YOLO(model_path)

        # Face DB
        self.face_db = FaceDB(DATASET_PATH)
        self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)

        # Cache recognized faces for N frames to reduce computation
        self._recognition_cache = {}  # box_index -> {"name": str, "ttl": int}

        # Person detection state for IoT
        self.persons_detected = 0

    def start_camera(self):
        """Open the webcam."""
        if self._started and self.cap and self.cap.isOpened():
            return True
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            logger.error("Could not open camera (index 0)")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._started = True
        # Reload face DB when starting camera (in case new students were added)
        self.face_db.reload()
        logger.info("Camera started (640x480)")
        return True

    def stop_camera(self):
        """Release the webcam."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self._started = False
        self.persons_detected = 0
        self._recognition_cache = {}
        logger.info("Camera stopped")

    def draw_corner_rect(self, img, x1, y1, x2, y2, color, thickness=2, length=18):
        """Draw professional corner-bracket style bounding box."""
        cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)
        cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + length), color, thickness)
        cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - length), color, thickness)
        cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - length), color, thickness)

    def _compute_attention(self, px1, py1, px2, py2, frame_w, frame_h, phone_detected, face_found):
        """
        Compute attention score (0-100):
        - Phone usage = 0%
        - Frontal face detected (looking straight) = 100%
        - Otherwise = 0%
        """
        if phone_detected:
            return 0
            
        if face_found:
            return 100
            
        return 0

    def process_frame(self):
        """
        Process one camera frame.
        Returns: (frame_base64, metadata_dict)
        """
        if not self.cap or not self.cap.isOpened():
            return None, {
                "error": "Camera not available",
                "num_persons": 0, "num_phones": 0, "average_engagement": 0,
                "students": [], "roster": self.attendance_manager.get_roster_summary(),
                "counts": self.attendance_manager.get_counts(),
            }

        success, frame = self.cap.read()
        if not success:
            return None, {
                "error": "Failed to read frame",
                "num_persons": 0, "num_phones": 0, "average_engagement": 0,
                "students": [], "roster": self.attendance_manager.get_roster_summary(),
                "counts": self.attendance_manager.get_counts(),
            }

        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        self.frame_count += 1
        frame_h, frame_w = frame.shape[:2]

        persons = []
        phones = []

        # ── YOLO Detection ────────────────────────────────────────────────────
        if self.yolo_model:
            results = self.yolo_model(frame, classes=[0, 67], verbose=False)
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    if conf > 0.4:
                        if cls == 0:
                            persons.append((x1, y1, x2, y2, conf))
                        elif cls == 67:
                            phones.append((x1, y1, x2, y2, conf))
        else:
            # FALLBACK: If YOLO is not available, use face cascade to find persons.
            # Expand the face box to simulate a person box.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_fallback = self.face_cascade.detectMultiScale(gray, 1.15, 5, minSize=(40, 40))
            for (x, y, w, h) in faces_fallback:
                px1 = max(0, x - int(w * 0.5))
                py1 = max(0, y - int(h * 0.5))
                px2 = min(frame_w, x + int(w * 1.5))
                py2 = min(frame_h, y + int(h * 3.0))
                persons.append((px1, py1, px2, py2, 1.0))

        self.persons_detected = len(persons)

        # ── Process Each Person ───────────────────────────────────────────────
        per_student_data = []
        total_engagement = 0

        for i, (px1, py1, px2, py2, pconf) in enumerate(persons):
            # Check phone overlap
            phone_detected = False
            for (phx1, phy1, phx2, phy2, _) in phones:
                if px1 < phx2 and px2 > phx1 and py1 < phy2 and py2 > phy1:
                    phone_detected = True
                    break

            # ── Face Detection within person bounding box ─────────────────────
            crop_y1, crop_y2 = max(0, py1), min(frame_h, py2)
            crop_x1, crop_x2 = max(0, px1), min(frame_w, px2)
            person_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            face_found = False
            student_name = None

            if person_crop.size > 0:
                gray_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)
                faces_in_person = self.face_cascade.detectMultiScale(
                    gray_crop, 1.15, 5, minSize=(40, 40)
                )
                face_found = len(faces_in_person) > 0

                # Check recognition cache
                cache_key = i
                if cache_key in self._recognition_cache and self._recognition_cache[cache_key]["ttl"] > 0:
                    student_name = self._recognition_cache[cache_key]["name"]
                    self._recognition_cache[cache_key]["ttl"] -= 1
                elif face_found and self.frame_count % 8 == 0:
                    # Run recognition on the detected face
                    fx, fy, fw, fh = max(faces_in_person, key=lambda f: f[2] * f[3])
                    face_crop = person_crop[fy:fy + fh, fx:fx + fw]
                    recognized_name, confidence = self.face_db.recognize(face_crop)
                    if recognized_name:
                        student_name = recognized_name
                        self._recognition_cache[cache_key] = {"name": recognized_name, "ttl": 12}

                    # Draw face rectangle inside person box
                    abs_fx = crop_x1 + fx
                    abs_fy = crop_y1 + fy
                    cv2.rectangle(display_frame, (abs_fx, abs_fy),
                                  (abs_fx + fw, abs_fy + fh), (0, 255, 255), 1)

            # Attention score
            attention = self._compute_attention(px1, py1, px2, py2, frame_w, frame_h,
                                                phone_detected, face_found)
            is_attentive = attention >= 50

            # Mark attendance
            display_name = "Unknown"
            if student_name:
                display_name = student_name.replace("_", " ").title()
                self.attendance_manager.mark_seen(display_name, phone_detected, is_attentive)

            # ── Draw on Frame ─────────────────────────────────────────────────
            if phone_detected:
                color = (0, 0, 255)  # Red
            elif student_name:
                color = (0, 255, 0)  # Green - recognized
            else:
                color = (255, 165, 0)  # Orange - unknown

            self.draw_corner_rect(display_frame, px1, py1, px2, py2, color, thickness=2)

            # Label
            label = display_name
            if phone_detected:
                label += " [PHONE]"
            label += f" {attention}%"

            t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
            cv2.rectangle(display_frame, (px1, py1 - 25), (px1 + t_size[0] + 10, py1), color, -1)
            cv2.putText(display_frame, label, (px1 + 5, py1 - 8),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

            total_engagement += attention
            per_student_data.append({
                "name": display_name,
                "phone": phone_detected,
                "attention": attention,
                "recognized": student_name is not None,
            })

        # Draw phone boxes
        for (phx1, phy1, phx2, phy2, _) in phones:
            cv2.rectangle(display_frame, (phx1, phy1), (phx2, phy2), (0, 0, 255), 2)
            cv2.putText(display_frame, "PHONE", (phx1, phy1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # ── Encode Frame ──────────────────────────────────────────────────────
        ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        frame_base64 = base64.b64encode(buffer).decode('utf-8') if ret else None

        avg_engagement = int(total_engagement / len(persons)) if persons else 0

        metadata = {
            "num_persons": len(persons),
            "num_phones": len(phones),
            "average_engagement": avg_engagement,
            "students": per_student_data,
            "roster": self.attendance_manager.get_roster_summary(),
            "counts": self.attendance_manager.get_counts(),
        }

        return frame_base64, metadata

    def release(self):
        """Release all resources."""
        self.stop_camera()
