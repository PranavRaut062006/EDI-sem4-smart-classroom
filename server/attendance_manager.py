"""
Smart Classroom — Attendance Manager
Handles class sessions, timer, and attendance logic with SQLite persistence.
"""

import uuid
import time
import threading
from datetime import datetime
from database import get_db


class AttendanceManager:
    def __init__(self):
        self.session_id = None
        self.timer_running = False
        self.timer_duration = 0       # total seconds
        self.timer_remaining = 0
        self.window_seconds = 0       # attendance window in seconds
        self.timer_start_time = None
        self._timer_thread = None

        # In-memory roster for the active session: {student_id: {...}}
        self.roster = {}

    # ── Session Lifecycle ─────────────────────────────────────────────────────

    def start_session(self, duration_min: int, window_min: int) -> str:
        """Start a new class session. Returns session_id."""
        self.session_id = str(uuid.uuid4())
        self.timer_duration = duration_min * 60
        self.window_seconds = window_min * 60
        self.timer_remaining = self.timer_duration
        self.timer_start_time = time.time()
        self.timer_running = True
        self.roster = {}

        now = datetime.now()

        with get_db() as db:
            # End any previous active session
            db.execute("UPDATE sessions SET status = 'ended', end_time = ? WHERE status = 'active'",
                       (now.strftime("%H:%M"),))

            # Create new session
            db.execute(
                """INSERT INTO sessions (id, date, start_time, duration_min, window_min, status)
                   VALUES (?, ?, ?, ?, ?, 'active')""",
                (self.session_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                 duration_min, window_min)
            )

            # Pre-populate attendance as 'absent' for all registered students
            students = db.execute("SELECT id, name, roll FROM students").fetchall()
            for s in students:
                record_id = str(uuid.uuid4())
                db.execute(
                    """INSERT INTO attendance (id, session_id, student_id, status)
                       VALUES (?, ?, ?, 'absent')""",
                    (record_id, self.session_id, s["id"])
                )
                self.roster[s["name"]] = {
                    "record_id": record_id,
                    "student_id": s["id"],
                    "name": s["name"],
                    "roll": s["roll"],
                    "status": "absent",
                    "entry_time": None,
                    "attention_frames": 0,
                    "total_frames": 0,
                    "phone_count": 0,
                }

        # Start background timer thread
        if self._timer_thread and self._timer_thread.is_alive():
            pass
        else:
            self._timer_thread = threading.Thread(target=self._run_timer, daemon=True)
            self._timer_thread.start()

        return self.session_id

    def stop_session(self):
        """End the current session and persist analytics."""
        self.timer_running = False
        self.timer_remaining = 0

        if not self.session_id:
            return

        now = datetime.now().strftime("%H:%M")

        with get_db() as db:
            db.execute(
                "UPDATE sessions SET status = 'ended', end_time = ? WHERE id = ?",
                (now, self.session_id)
            )

            # Persist analytics for each student
            for name, data in self.roster.items():
                att_pct = 0
                if data["total_frames"] > 0:
                    att_pct = round((data["attention_frames"] / data["total_frames"]) * 100)

                existing = db.execute(
                    "SELECT id FROM analytics WHERE session_id = ? AND student_id = ?",
                    (self.session_id, data["student_id"])
                ).fetchone()

                if existing:
                    db.execute(
                        """UPDATE analytics SET attention_pct = ?, phone_count = ?, updated_at = ?
                           WHERE session_id = ? AND student_id = ?""",
                        (att_pct, data["phone_count"], datetime.now().isoformat(),
                         self.session_id, data["student_id"])
                    )
                else:
                    db.execute(
                        """INSERT INTO analytics (id, session_id, student_id, attention_pct, phone_count)
                           VALUES (?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), self.session_id, data["student_id"],
                         att_pct, data["phone_count"])
                    )

        self.session_id = None

    def _run_timer(self):
        while self.timer_running and self.timer_remaining > 0:
            time.sleep(1)
            elapsed = time.time() - self.timer_start_time
            self.timer_remaining = max(0, self.timer_duration - elapsed)

        if self.timer_remaining <= 0 and self.timer_running:
            self.timer_running = False
            # Auto-stop session when timer expires
            self.stop_session()

    def get_timer_state(self):
        return {
            "running": self.timer_running,
            "duration": self.timer_duration,
            "remaining": round(self.timer_remaining),
            "sessionId": self.session_id,
        }

    # ── Attendance Marking ────────────────────────────────────────────────────

    def mark_seen(self, student_name: str, phone_detected: bool = False, is_attentive: bool = True):
        """Called by vision engine when a student is recognized in a frame."""
        if student_name not in self.roster:
            return  # not a registered student for this session

        data = self.roster[student_name]
        data["total_frames"] += 1

        if is_attentive and not phone_detected:
            data["attention_frames"] += 1

        if phone_detected:
            data["phone_count"] += 1

        # Mark attendance if still absent
        if data["status"] == "absent" and self.session_id:
            now = datetime.now()
            entry_time = now.strftime("%H:%M:%S")
            data["entry_time"] = entry_time

            if self.timer_running:
                elapsed = time.time() - self.timer_start_time
                if elapsed <= self.window_seconds:
                    data["status"] = "present"
                else:
                    data["status"] = "late"
            else:
                data["status"] = "late"

            # Persist to DB
            with get_db() as db:
                db.execute(
                    """UPDATE attendance SET status = ?, entry_time = ?, updated_at = ?
                       WHERE id = ?""",
                    (data["status"], entry_time, now.isoformat(), data["record_id"])
                )

    def get_roster_summary(self) -> list:
        """Return current in-memory roster as a list for WebSocket."""
        result = []
        for name, data in self.roster.items():
            att_pct = 0
            if data["total_frames"] > 0:
                att_pct = round((data["attention_frames"] / data["total_frames"]) * 100)
            result.append({
                "name": data["name"],
                "roll": data["roll"],
                "status": data["status"],
                "entryTime": data["entry_time"] or "--:--",
                "attentionPct": att_pct,
                "phoneCount": data["phone_count"],
                "recordId": data["record_id"],
                "studentId": data["student_id"],
            })
        return result

    def get_counts(self) -> dict:
        present = sum(1 for d in self.roster.values() if d["status"] == "present")
        late = sum(1 for d in self.roster.values() if d["status"] == "late")
        absent = sum(1 for d in self.roster.values() if d["status"] == "absent")
        return {"present": present, "late": late, "absent": absent, "total": len(self.roster)}
