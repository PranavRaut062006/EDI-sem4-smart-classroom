"""
Smart Classroom AI — Configuration
All environment-specific settings live here.
Copy .env.example → .env and adjust values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STUDENTS_DIR = DATA_DIR / "students"   # face images stored here
SESSIONS_DIR = DATA_DIR / "sessions"   # SQLite DB files stored here

# Ensure data directories exist on startup
STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    # ── Flask ──────────────────────────────────────────────────────────────────
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    # ── Database ───────────────────────────────────────────────────────────────
    # SQLite — zero-config, file-based, RPi-friendly
    DATABASE_PATH = str(SESSIONS_DIR / "smartclassroom.db")

    # ── Camera ─────────────────────────────────────────────────────────────────
    # 0 = default webcam; on Raspberry Pi with PiCamera use 0 or /dev/video0
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))
    CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", 640))
    CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", 480))
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", 15))

    # ── Face Recognition ──────────────────────────────────────────────────────
    FACE_RECOGNITION_TOLERANCE = float(os.getenv("FACE_TOLERANCE", 0.55))
    STUDENTS_IMAGES_DIR = str(STUDENTS_DIR)

    # ── Attendance ─────────────────────────────────────────────────────────────
    # Default class duration and attendance window (in minutes)
    DEFAULT_CLASS_DURATION = int(os.getenv("CLASS_DURATION", 60))
    DEFAULT_ATTENDANCE_WINDOW = int(os.getenv("ATTENDANCE_WINDOW", 10))

    # ── IoT / GPIO ─────────────────────────────────────────────────────────────
    # Set to True only on Raspberry Pi with GPIO wiring
    GPIO_ENABLED = os.getenv("GPIO_ENABLED", "false").lower() == "true"
    GPIO_LIGHTS_PIN = int(os.getenv("GPIO_LIGHTS_PIN", 17))
    GPIO_FANS_PIN = int(os.getenv("GPIO_FANS_PIN", 27))

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Frontend dev server origin (Vite default: 5173)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
