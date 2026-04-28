"""
Camera Utility
Provides a thin wrapper around OpenCV's VideoCapture.
Designed for Raspberry Pi (CSI/USB camera) and Windows webcam.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv-python not installed. Camera will be unavailable.")


class Camera:
    """
    Thread-safe camera wrapper. Reads frames in a background thread
    to avoid blocking the Flask request handlers.

    Usage:
        cam = Camera(index=0, width=640, height=480, fps=15)
        cam.start()
        frame = cam.read()   # numpy RGB array or None
        cam.stop()
    """

    def __init__(self, index: int = 0, width: int = 640, height: int = 480, fps: int = 15):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None
        self._frame: Optional[object] = None
        self._running = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if not CV2_AVAILABLE:
            logger.error("Cannot start camera: opencv-python not installed.")
            return False

        self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            logger.error("Camera index %d could not be opened.", self.index)
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera started (index=%d, %dx%d @ %dfps)", self.index, self.width, self.height, self.fps)
        return True

    def _capture_loop(self):
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                # Convert BGR (OpenCV default) → RGB (face_recognition expects RGB)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._frame = rgb_frame

    def read(self):
        """Return the latest captured RGB frame, or None if unavailable."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def read_jpeg(self) -> Optional[bytes]:
        """Return the latest frame as JPEG bytes (for streaming to frontend)."""
        if not CV2_AVAILABLE:
            return None
        frame = self.read()
        if frame is None:
            return None
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
        logger.info("Camera stopped.")

    @property
    def is_running(self) -> bool:
        return self._running
