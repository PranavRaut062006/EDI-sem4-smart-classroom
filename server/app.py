"""
Smart Classroom — Unified FastAPI Backend
All REST endpoints + WebSocket for real-time camera streaming.
"""

import asyncio
import sys
import os
import json
import uuid
import base64
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add server directory to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_db
from attendance_manager import AttendanceManager
from vision_engine import VisionEngine, DATASET_PATH
import iot_controller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── App Lifecycle ─────────────────────────────────────────────────────────────

attendance_mgr = AttendanceManager()
vision_engine = VisionEngine(attendance_mgr)


def sync_dataset_to_db():
    """Import existing dataset student folders into the SQLite DB if not already there."""
    if not os.path.exists(DATASET_PATH):
        return

    with get_db() as db:
        for folder_name in os.listdir(DATASET_PATH):
            folder_path = os.path.join(DATASET_PATH, folder_name)
            if not os.path.isdir(folder_path):
                continue

            # Check if already in DB
            existing = db.execute("SELECT id FROM students WHERE folder = ?", (folder_name,)).fetchone()
            if existing:
                continue

            # Read metadata if available
            meta_path = os.path.join(folder_path, "metadata.json")
            name = folder_name.replace("_", " ").title()
            roll = f"AUTO-{folder_name.upper()}"
            student_id = str(uuid.uuid4())

            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    name = meta.get("name", name)
                    roll = meta.get("roll", meta.get("id", roll))
                    student_id = meta.get("id", student_id)
                except Exception:
                    pass

            db.execute(
                "INSERT OR IGNORE INTO students (id, name, roll, folder) VALUES (?, ?, ?, ?)",
                (student_id, name, roll, folder_name)
            )
            logger.info("Synced dataset student: %s (%s)", name, folder_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    os.makedirs(DATASET_PATH, exist_ok=True)
    sync_dataset_to_db()
    logger.info("Database initialized. Dataset path: %s", DATASET_PATH)
    yield
    # Shutdown
    vision_engine.release()
    logger.info("Vision engine released.")


app = FastAPI(title="Smart Classroom API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REST ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "camera": vision_engine._started}


# ── Student Registration ─────────────────────────────────────────────────────

@app.post("/api/register")
async def register_student(request: Request):
    """Register a student with name, roll, and base64 image."""
    data = await request.json()
    name = data.get("name", "").strip()
    roll = data.get("roll", "").strip()
    image_b64 = data.get("image", "")

    if not name or not roll:
        return JSONResponse({"error": "Name and roll number are required"}, status_code=400)

    if not image_b64:
        return JSONResponse({"error": "No image data provided"}, status_code=400)

    # Decode image
    if "," in image_b64:
        image_b64 = image_b64.split(",")[1]

    try:
        img_data = base64.b64decode(image_b64)
    except Exception:
        return JSONResponse({"error": "Invalid image data"}, status_code=400)

    student_id = str(uuid.uuid4())
    folder_name = name.replace(" ", "_").lower()

    # Save image to dataset folder
    student_dir = os.path.join(DATASET_PATH, folder_name)
    os.makedirs(student_dir, exist_ok=True)
    img_path = os.path.join(student_dir, "face_anchor.jpg")

    with open(img_path, "wb") as f:
        f.write(img_data)

    # Save metadata
    meta_path = os.path.join(student_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump({
            "id": student_id,
            "name": name,
            "roll": roll,
            "registered_at": datetime.now().isoformat(),
        }, f)

    # Insert into database
    with get_db() as db:
        # Check duplicate roll
        existing = db.execute("SELECT id FROM students WHERE roll = ?", (roll,)).fetchone()
        if existing:
            return JSONResponse({"error": f"Roll number '{roll}' already registered"}, status_code=409)

        db.execute(
            "INSERT INTO students (id, name, roll, folder) VALUES (?, ?, ?, ?)",
            (student_id, name, roll, folder_name)
        )

    # Reload face database so the new student is recognized
    vision_engine.face_db.reload()

    return JSONResponse({
        "status": "success",
        "message": f"Student '{name}' registered successfully",
        "student": {"id": student_id, "name": name, "roll": roll, "folder": folder_name},
    })


@app.get("/api/students")
async def list_students():
    """List all registered students."""
    with get_db() as db:
        rows = db.execute("SELECT * FROM students ORDER BY roll ASC").fetchall()
        students = [
            {
                "id": r["id"],
                "name": r["name"],
                "roll": r["roll"],
                "folder": r["folder"],
                "createdAt": r["created_at"],
            }
            for r in rows
        ]
    return JSONResponse({"students": students})


@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    """Remove a student and their face data."""
    with get_db() as db:
        row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not row:
            return JSONResponse({"error": "Student not found"}, status_code=404)

        # Remove face image folder
        if row["folder"]:
            import shutil
            folder_path = os.path.join(DATASET_PATH, row["folder"])
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)

        db.execute("DELETE FROM students WHERE id = ?", (student_id,))

    # Reload face database
    vision_engine.face_db.reload()

    return JSONResponse({"message": f"Student '{row['name']}' removed"})


# ── Session Management ────────────────────────────────────────────────────────

@app.post("/api/sessions/start")
async def start_session(request: Request):
    """Start a new class session."""
    data = await request.json()
    duration = int(data.get("durationMin", 60))
    window = int(data.get("windowMin", 10))

    # Start camera if not running
    if not vision_engine._started:
        vision_engine.start_camera()

    session_id = attendance_mgr.start_session(duration, window)
    return JSONResponse({"status": "success", "sessionId": session_id, "message": "Session started"})


@app.post("/api/sessions/stop")
async def stop_session():
    """End the active session."""
    attendance_mgr.stop_session()
    return JSONResponse({"status": "success", "message": "Session ended"})


@app.get("/api/sessions")
async def list_sessions():
    """List all past sessions."""
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM sessions ORDER BY date DESC, start_time DESC"
        ).fetchall()
        sessions = [
            {
                "id": r["id"],
                "date": r["date"],
                "startTime": r["start_time"],
                "endTime": r["end_time"],
                "durationMin": r["duration_min"],
                "windowMin": r["window_min"],
                "status": r["status"],
            }
            for r in rows
        ]
    return JSONResponse({"sessions": sessions})


@app.get("/api/sessions/{session_id}/records")
async def get_session_records(session_id: str):
    """Get attendance records for a session."""
    with get_db() as db:
        rows = db.execute(
            """SELECT a.*, s.name, s.roll
               FROM attendance a
               JOIN students s ON s.id = a.student_id
               WHERE a.session_id = ?
               ORDER BY a.entry_time ASC""",
            (session_id,)
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
    return JSONResponse({"records": records})


@app.get("/api/sessions/{session_id}/summary")
async def session_summary(session_id: str):
    """Get attendance summary counts for a session."""
    with get_db() as db:
        rows = db.execute(
            "SELECT status, COUNT(*) as cnt FROM attendance WHERE session_id = ? GROUP BY status",
            (session_id,)
        ).fetchall()
        summary = {r["status"]: r["cnt"] for r in rows}
    return JSONResponse({
        "present": summary.get("present", 0),
        "late": summary.get("late", 0),
        "absent": summary.get("absent", 0),
        "total": sum(summary.values()),
    })


# ── Attendance Override ───────────────────────────────────────────────────────

@app.put("/api/attendance/{record_id}")
async def update_attendance(record_id: str, request: Request):
    """Override attendance status for a student."""
    data = await request.json()
    status = data.get("status")
    if status not in ("present", "late", "absent"):
        return JSONResponse({"error": "Invalid status"}, status_code=400)

    with get_db() as db:
        db.execute(
            "UPDATE attendance SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), record_id)
        )
    return JSONResponse({"message": "Attendance updated"})


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics/{session_id}")
async def get_analytics(session_id: str):
    """Get attention analytics for a session."""
    with get_db() as db:
        rows = db.execute(
            """SELECT an.*, s.name, s.roll
               FROM analytics an
               JOIN students s ON s.id = an.student_id
               WHERE an.session_id = ?
               ORDER BY an.attention_pct DESC""",
            (session_id,)
        ).fetchall()

        if not rows:
            return JSONResponse({
                "analytics": [],
                "summary": {"avgAttention": 0, "totalPhoneEvents": 0,
                             "lowAttentionCount": 0, "trackedCount": 0}
            })

        data = [
            {
                "studentId": r["student_id"],
                "name": r["name"],
                "roll": r["roll"],
                "attentionPct": r["attention_pct"],
                "phoneCount": r["phone_count"],
            }
            for r in rows
        ]

        total = len(data)
        avg_att = round(sum(d["attentionPct"] for d in data) / total) if total else 0
        total_phones = sum(d["phoneCount"] for d in data)
        low_att = sum(1 for d in data if d["attentionPct"] < 50)

    return JSONResponse({
        "analytics": data,
        "summary": {
            "avgAttention": avg_att,
            "totalPhoneEvents": total_phones,
            "lowAttentionCount": low_att,
            "trackedCount": total,
        }
    })


# ── IoT Control ───────────────────────────────────────────────────────────────

@app.get("/api/iot/status")
async def iot_status():
    """Get current IoT device states."""
    status = iot_controller.get_status()
    activity = iot_controller.get_recent_activity()
    return JSONResponse({**status, "recentActivity": activity})


@app.post("/api/iot/control")
async def iot_control(request: Request):
    """Manual device control."""
    data = await request.json()
    device = data.get("device")
    state = data.get("state")

    if device not in ("lights", "fans"):
        return JSONResponse({"error": "Invalid device"}, status_code=400)

    on = state == "ON" if isinstance(state, str) else bool(state)

    success = iot_controller.manual_control(device, on)
    if not success:
        return JSONResponse({"error": "Disable Auto Mode to control manually"}, status_code=400)

    return JSONResponse({"message": f"{device.capitalize()} turned {'ON' if on else 'OFF'}"})


@app.post("/api/iot/auto-mode")
async def iot_auto_mode(request: Request):
    """Toggle auto mode."""
    data = await request.json()
    enabled = bool(data.get("enabled", True))
    iot_controller.set_auto_mode(enabled)
    return JSONResponse({"message": f"Auto mode {'enabled' if enabled else 'disabled'}"})


# ── Camera Control ────────────────────────────────────────────────────────────

@app.post("/api/camera/start")
async def start_camera():
    # Camera lifecycle is now managed by the WebSocket ConnectionManager
    return JSONResponse({"status": "success", "message": "Camera start acknowledged"})

@app.post("/api/camera/stop")
async def stop_camera():
    # Camera lifecycle is now managed by the WebSocket ConnectionManager
    return JSONResponse({"status": "success", "message": "Camera stop acknowledged"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBSOCKET — Real-time camera + data streaming
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.bg_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
        
        # Auto-start camera when first client connects
        if not vision_engine._started:
            vision_engine.start_camera()
            
        # Start broadcast loop if not running
        if self.bg_task is None or self.bg_task.done():
            self.bg_task = asyncio.create_task(self.broadcast_loop())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
            
        # Stop camera when last client disconnects
        if not self.active_connections:
            vision_engine.stop_camera()
            if self.bg_task:
                self.bg_task.cancel()
                self.bg_task = None

    async def broadcast_loop(self):
        try:
            while self.active_connections:
                frame_b64, vision_meta = vision_engine.process_frame()
                
                # Update IoT based on person detection
                iot_controller.update_person_detection(vision_meta.get("num_persons", 0) > 0)
                
                timer_state = attendance_mgr.get_timer_state()
                iot_status = iot_controller.get_status()

                payload = {
                    "frame": frame_b64,
                    "vision": vision_meta,
                    "timer": timer_state,
                    "iot": iot_status,
                }
                
                payload_str = json.dumps(payload)
                
                # Broadcast to all active clients
                dead_connections = []
                for connection in self.active_connections:
                    try:
                        await connection.send_text(payload_str)
                    except Exception:
                        dead_connections.append(connection)
                        
                for dead in dead_connections:
                    self.disconnect(dead)
                    
                await asyncio.sleep(0.2)  # ~5 fps for smoother video
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open and listen for messages (if any)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
