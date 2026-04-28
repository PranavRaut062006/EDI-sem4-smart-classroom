"""
Attention Monitoring Service
Evaluates student attentiveness based on head pose and phone detection.
Designed to be called once per camera frame during an active session.

This is a stub implementation — replace the placeholder logic with
your actual head-pose estimation and phone detection model.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StudentAttentionState:
    student_id: str
    frames_total: int = 0
    frames_attentive: int = 0
    phone_events: int = 0

    @property
    def attention_pct(self) -> int:
        if self.frames_total == 0:
            return 0
        return round((self.frames_attentive / self.frames_total) * 100)


class AttentionMonitor:
    """
    Tracks per-student attention across frames for a session.
    Instantiate once per session.
    """

    def __init__(self):
        self._states: dict[str, StudentAttentionState] = {}

    def process_frame(self, detections: list[dict]):
        """
        Update attention state from one camera frame.

        detections: list of {
            "studentId": str,
            "isAttentive": bool,   # face facing forward
            "phoneDetected": bool,
        }
        """
        for det in detections:
            sid = det.get("studentId")
            if not sid:
                continue

            if sid not in self._states:
                self._states[sid] = StudentAttentionState(student_id=sid)

            state = self._states[sid]
            state.frames_total += 1

            if det.get("isAttentive", False):
                state.frames_attentive += 1

            if det.get("phoneDetected", False):
                state.phone_events += 1

    def get_summary(self) -> list[dict]:
        """Return current attention summary for all tracked students."""
        return [
            {
                "studentId": s.student_id,
                "attentionPct": s.attention_pct,
                "phoneCount": s.phone_events,
                "framesTotal": s.frames_total,
            }
            for s in self._states.values()
        ]

    def get_student_summary(self, student_id: str) -> dict | None:
        s = self._states.get(student_id)
        if not s:
            return None
        return {
            "studentId": s.student_id,
            "attentionPct": s.attention_pct,
            "phoneCount": s.phone_events,
        }

    def reset(self):
        """Call at the start of a new session."""
        self._states.clear()


def is_facing_forward(landmarks: dict | None) -> bool:
    """
    TODO: Implement head-pose estimation using facial landmarks.
    Return True if the student's face is oriented toward the camera (< 30° yaw).

    Placeholder: always returns True.
    Integration point: use mediapipe FaceMesh or dlib landmarks.
    """
    return True  # placeholder


def phone_detected_in_frame(frame) -> bool:
    """
    TODO: Implement phone detection in the given frame.
    Return True if a mobile phone is visible.

    Placeholder: always returns False.
    Integration point: use YOLOv8-nano (coco) or MobileNet SSD trained on phones.
    """
    return False  # placeholder
