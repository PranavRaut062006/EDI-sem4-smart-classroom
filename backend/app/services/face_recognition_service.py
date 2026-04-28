"""
Face Recognition Service
Loads known student face encodings from data/students/ at startup,
then matches faces detected in each camera frame.

INSTALLATION NOTE (Windows):
    pip install cmake
    pip install dlib
    pip install face-recognition

INSTALLATION NOTE (Raspberry Pi):
    sudo apt install -y libatlas-base-dev libhdf5-dev cmake
    pip install face-recognition

This module is guarded by a try/except so the backend starts even if
face_recognition is not installed (useful for UI-only development on Windows).
"""

import os
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

try:
    import face_recognition
    import numpy as np
    FR_AVAILABLE = True
except ImportError:
    FR_AVAILABLE = False
    logger.warning(
        "face_recognition not installed. "
        "Face matching will be unavailable. "
        "See installation instructions in face_recognition_service.py"
    )

# In-memory cache of known encodings
_known_encodings: list = []
_known_ids: list[str] = []
_known_names: list[str] = []


def reload_embeddings(students_dir: str | None = None) -> int:
    """
    Load (or reload) face encodings from all images in the students directory.
    Returns the number of students successfully encoded.
    Call this after registering a new student.
    """
    global _known_encodings, _known_ids, _known_names

    if not FR_AVAILABLE:
        logger.warning("face_recognition unavailable — skipping embedding load.")
        return 0

    if students_dir is None:
        students_dir = current_app.config["STUDENTS_IMAGES_DIR"]

    encodings, ids, names = [], [], []

    for img_file in Path(students_dir).iterdir():
        if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue

        student_id = img_file.stem  # filename = <uuid>.<ext>

        try:
            image = face_recognition.load_image_file(str(img_file))
            enc_list = face_recognition.face_encodings(image)
            if enc_list:
                encodings.append(enc_list[0])
                ids.append(student_id)
                names.append(img_file.name)
            else:
                logger.warning("No face found in %s — skipping", img_file.name)
        except Exception as exc:
            logger.error("Error encoding %s: %s", img_file.name, exc)

    _known_encodings = encodings
    _known_ids = ids
    _known_names = names
    logger.info("Loaded %d face encodings.", len(encodings))
    return len(encodings)


def identify_faces(rgb_frame) -> list[dict]:
    """
    Detect and identify all faces in an RGB frame.

    Returns a list of dicts:
        { "studentId": str | None, "location": (top, right, bottom, left) }

    studentId is None for unknown faces.
    """
    if not FR_AVAILABLE:
        return []

    if not _known_encodings:
        logger.debug("No known encodings loaded — call reload_embeddings() first.")
        return []

    tolerance = 0.55
    try:
        tolerance = current_app.config.get("FACE_RECOGNITION_TOLERANCE", 0.55)
    except RuntimeError:
        pass  # outside app context

    locations = face_recognition.face_locations(rgb_frame, model="hog")
    encodings = face_recognition.face_encodings(rgb_frame, locations)

    results = []
    for enc, loc in zip(encodings, locations):
        distances = face_recognition.face_distance(_known_encodings, enc)
        best_idx = int(np.argmin(distances)) if len(distances) > 0 else -1

        if best_idx >= 0 and distances[best_idx] <= tolerance:
            student_id = _known_ids[best_idx]
        else:
            student_id = None  # unknown face

        results.append({"studentId": student_id, "location": loc})

    return results
