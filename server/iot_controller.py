"""
Smart Classroom — IoT Controller
Simulates lights/fans control based on person detection.
Auto mode: turns devices ON when person detected, OFF when empty.
"""

import uuid
import logging
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

# In-memory device state
_state = {
    "lights": False,
    "fans": False,
    "auto_mode": True,
    "person_detected": False,
}

# Activity log (in-memory, recent 50 entries)
_activity_log = []


def get_status() -> dict:
    """Return current IoT status."""
    return {
        "lights": _state["lights"],
        "fans": _state["fans"],
        "autoMode": _state["auto_mode"],
        "personDetected": _state["person_detected"],
    }


def get_recent_activity() -> list:
    """Return recent activity log entries."""
    try:
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM iot_log ORDER BY timestamp DESC LIMIT 15"
            ).fetchall()
            return [
                {
                    "time": r["timestamp"][-8:-3] if r["timestamp"] else "??:??",
                    "event": f"{'Auto' if r['trigger'] == 'auto' else 'Manual'}: "
                             f"{r['device'].capitalize()} turned {r['state']}",
                }
                for r in rows
            ]
    except Exception:
        return []


def set_auto_mode(enabled: bool):
    _state["auto_mode"] = enabled


def set_device(device: str, on: bool, trigger: str = "manual"):
    """Set a device ON/OFF and log it."""
    if device not in ("lights", "fans"):
        return

    old = _state[device]
    _state[device] = on

    # Only log if state actually changed
    if old != on:
        state_str = "ON" if on else "OFF"
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO iot_log (id, device, state, trigger) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), device, state_str, trigger)
                )
        except Exception as e:
            logger.warning("Failed to log IoT event: %s", e)


def update_person_detection(detected: bool):
    """
    Called by vision engine each frame.
    In auto mode, toggles lights/fans based on presence.
    """
    _state["person_detected"] = detected

    if _state["auto_mode"]:
        if detected and not _state["lights"]:
            set_device("lights", True, "auto")
            set_device("fans", True, "auto")
        elif not detected and _state["lights"]:
            set_device("lights", False, "auto")
            set_device("fans", False, "auto")


def manual_control(device: str, on: bool) -> bool:
    """Manual control — only works when auto mode is OFF."""
    if _state["auto_mode"]:
        return False
    set_device(device, on, "manual")
    return True
