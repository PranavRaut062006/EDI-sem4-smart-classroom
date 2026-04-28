"""
IoT Control API — /api/iot
Controls classroom lights and fans via GPIO (on RPi) or simulated state (on PC).
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_db
from app.services.iot_service import set_device_state, get_device_states

iot_bp = Blueprint("iot", __name__)


def _log_event(db, device: str, state: str, trigger: str):
    db.execute(
        "INSERT INTO iot_log (id, device, state, trigger) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), device, state, trigger),
    )


# ── GET /api/iot/status ───────────────────────────────────────────────────────
@iot_bp.get("/status")
def get_status():
    """Return current state of lights, fans, and person detection."""
    states = get_device_states()
    db = get_db()
    logs = db.execute(
        "SELECT * FROM iot_log ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()
    recent = [
        {"time": r["timestamp"][-8:-3], "event": f"{'Auto' if r['trigger'] == 'auto' else 'Manual'}: {r['device'].capitalize()} turned {r['state']}"}
        for r in logs
    ]
    return jsonify({**states, "recentActivity": recent})


# ── POST /api/iot/control ─────────────────────────────────────────────────────
@iot_bp.post("/control")
def control_device():
    """
    Manual device control.
    Body: { device: 'lights' | 'fans', state: 'ON' | 'OFF' }
    """
    data = request.get_json(silent=True) or {}
    device = data.get("device")
    state = data.get("state")

    if device not in ("lights", "fans"):
        return jsonify({"error": "device must be 'lights' or 'fans'"}), 400
    if state not in ("ON", "OFF"):
        return jsonify({"error": "state must be 'ON' or 'OFF'"}), 400

    set_device_state(device, state == "ON")

    db = get_db()
    _log_event(db, device, state, "manual")
    db.commit()

    return jsonify({"message": f"{device.capitalize()} turned {state}"})


# ── POST /api/iot/auto-update ─────────────────────────────────────────────────
@iot_bp.post("/auto-update")
def auto_update():
    """
    Called by the presence detection service when person detection changes.
    Body: { personDetected: bool }
    """
    data = request.get_json(silent=True) or {}
    person_detected = bool(data.get("personDetected", False))

    new_state = "ON" if person_detected else "OFF"
    db = get_db()

    for device in ("lights", "fans"):
        set_device_state(device, person_detected)
        _log_event(db, device, new_state, "auto")

    db.commit()

    reason = "person detected" if person_detected else "no person in room"
    return jsonify({
        "message": f"Auto: lights and fans set to {new_state} ({reason})",
        "lights": new_state,
        "fans": new_state,
    })
