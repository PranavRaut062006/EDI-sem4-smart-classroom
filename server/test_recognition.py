import cv2
import os
from vision_engine import FaceDB, DATASET_PATH

db = FaceDB(DATASET_PATH)
db.reload()
print("Known faces:", db.known_faces.keys())

# Load a test image (e.g. from dataset or webcam)
for name in db.known_faces.keys():
    path = os.path.join(DATASET_PATH, name, "face_anchor.jpg")
    img = cv2.imread(path)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = db.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_crop = img[y:y + h, x:x + w]
        recognized_name, score = db.recognize(face_crop)
        print(f"Testing {name}: Recognized as {recognized_name} with score {score}")
        
        # Test descriptor match manually to see the exact score
        desc = db._compute_face_descriptor(face_crop)
        import numpy as np
        for known_name, known_desc in db.known_faces.items():
            score = np.dot(desc, known_desc) / (
                np.linalg.norm(desc) * np.linalg.norm(known_desc) + 1e-8
            )
            print(f"  vs {known_name}: {score}")
    else:
        print(f"No face detected in {name}'s anchor image.")
