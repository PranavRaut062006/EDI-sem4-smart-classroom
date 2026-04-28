"""
Attendance API — /api/attendance
Handles session creation and per-student attendance records.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models.database import get_db

attendance_bp = Blueprint("attendance", __name__)


def _session_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "date": row["date"],
        "startTime": row["start_time"],
        "endTime": row["end_time"],
        "durationMin": row["duration_min"],
        "windowMin": row["window_min"],
        "status": row["status"],
    }


def _record_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "studentId": row["student_id"],
        "entryTime": row["entry_time"],
        "status": row["status"],
        "updatedAt": row["updated_at"],
    }


# ── Sessions ──────────────────────────────────────────────────────────────────

@attendance_bp.post("/sessions")
def start_session():
    """Create a new class session. Body: { durationMin, windowMin }"""
    data = request.get_json(silent=True) or {}
    duration_min = int(data.get("durationMin", 60))
    window_min = int(data.get("windowMin", 10))

    session_id = str(uuid.uuid4())
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    db = get_db()

    # Mark any previously active session as ended
    db.execute(
        "UPDATE sessions SET status = 'ended' WHERE status = 'active'"
    )

    db.execute(
        """INSERT INTO sessions (id, date, start_time, duration_min, window_min, status)
           VALUES (?, ?, ?, ?, ?, 'active')""",
        (session_id, today, now, duration_min, window_min),
    )

    # Pre-populate attendance rows as 'absent' for all registered students
    students = db.execute("SELECT id FROM students").fetchall()
    for s in students:
        record_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO attendance (id, session_id, student_id, status)
               VALUES (?, ?, ?, 'absent')""",
            (record_id, session_id, s["id"]),
        )

    db.commit()
    return jsonify({"message": "Session started", "sessionId": session_id}), 201


@attendance_bp.put("/sessions/<string:session_id>/end")
def end_session(session_id: str):
    """End an active session."""
    db = get_db()
    now = datetime.now().strftime("%H:%M")
    db.execute(
        "UPDATE sessions SET status = 'ended', end_time = ? WHERE id = ?",
        (now, session_id),
    )
    db.commit()
    return jsonify({"message": "Session ended"})


@attendance_bp.get("/sessions")
def list_sessions():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM sessions ORDER BY date DESC, start_time DESC"
    ).fetchall()
    return jsonify({"sessions": [_session_to_dict(r) for r in rows]})


@attendance_bp.get("/sessions/active")
def active_session():
    db = get_db()
    row = db.execute(
        "SELECT * FROM sessions WHERE status = 'active' LIMIT 1"
    ).fetchone()
    if not row:
        return jsonify({"session": None})
    return jsonify({"session": _session_to_dict(row)})


# ── Attendance Records ─────────────────────────────────────────────────────────

@attendance_bp.get("/sessions/<string:session_id>/records")
def get_records(session_id: str):
    """Return all attendance records for a session, joined with student info."""
    db = get_db()
    rows = db.execute(
        """
        SELECT a.*, s.name, s.roll
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE a.session_id = ?
        ORDER BY a.entry_time ASC NULLS LAST
        """,
        (session_id,),
    ).fetchall()
    records = [
        {
            "id": r["id"],
            "studentId": r["student_id"],
            "name": r["name"],
            "roll": r["roll"],
            "entryTime": r["entry_time"],
            "status": r["status"],
        }
        for r in rows
    ]
    return jsonify({"records": records})


@attendance_bp.put("/records/<string:record_id>")
def update_record(record_id: str):
    """
    Override attendance status for a student.
    Body: { status: 'present' | 'late' | 'absent' }
    """
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("present", "late", "absent"):
        return jsonify({"error": "status must be 'present', 'late', or 'absent'"}), 400

    db = get_db()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    db.execute(
        "UPDATE attendance SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, record_id),
    )
    db.commit()
    return jsonify({"message": "Attendance updated"})


# ── Summary ───────────────────────────────────────────────────────────────────

@attendance_bp.get("/sessions/<string:session_id>/summary")
def session_summary(session_id: str):
    db = get_db()
    rows = db.execute(
        "SELECT status, COUNT(*) as cnt FROM attendance WHERE session_id = ? GROUP BY status",
        (session_id,),
    ).fetchall()
    summary = {r["status"]: r["cnt"] for r in rows}
    return jsonify({
        "present": summary.get("present", 0),
        "late": summary.get("late", 0),
        "absent": summary.get("absent", 0),
        "total": sum(summary.values()),
    })
