import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
import base64

from sensor_simulator import SensorSimulator
from vision_engine import VisionEngine
from attendance_manager import AttendanceManager

app = FastAPI()

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure core directories exist
os.makedirs("dataset", exist_ok=True)

attendance_mgr = AttendanceManager("dataset")
sensor_sim = SensorSimulator()
vision_engine = VisionEngine(attendance_mgr)

# ─── REST APIs ───

@app.post("/api/register")
async def register_student(request: Request):
    data = await request.json()
    first_name = data.get("firstName", "Unknown")
    last_name = data.get("lastName", "")
    full_name = f"{first_name}_{last_name}".strip("_")
    student_id = data.get("studentId", "STU_TEMP")
    email = data.get("email", "")
    phone = data.get("phone", "")
    course = data.get("course", "")
    image_b64 = data.get("image", "")

    if not image_b64:
        return JSONResponse({"status": "error", "message": "No image data"}, status_code=400)

    if "," in image_b64:
        image_b64 = image_b64.split(",")[1]
    img_data = base64.b64decode(image_b64)

    student_dir = os.path.join("dataset", full_name)
    os.makedirs(student_dir, exist_ok=True)
    img_path = os.path.join(student_dir, "face_anchor.jpg")
    meta_path = os.path.join(student_dir, "metadata.json")

    with open(img_path, "wb") as f:
        f.write(img_data)
        
    metadata = {
        "id": student_id,
        "name": full_name.replace("_", " "),
        "email": email,
        "phone": phone,
        "course": course,
        "registered_at": datetime.now().isoformat()
    }
    
    with open(meta_path, "w") as f:
        json.dump(metadata, f)

    # Clear deepface cache
    for cache_name in ["representations_vgg_face.pkl", "representations_facenet.pkl", "representations_facenet512.pkl"]:
        cache_file = os.path.join("dataset", cache_name)
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except:
                pass

    attendance_mgr.add_new_student(full_name)
    return JSONResponse({"status": "success", "message": f"Biometrically Verified: Registered {full_name}"})

@app.get("/api/students")
async def get_students():
    students = []
    if not os.path.exists("dataset"):
        return JSONResponse(students)
        
    for student_folder in os.listdir("dataset"):
        folder_path = os.path.join("dataset", student_folder)
        if os.path.isdir(folder_path):
            meta_path = os.path.join(folder_path, "metadata.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    students.append(json.load(f))
            else:
                students.append({
                    "id": f"ID_{student_folder}",
                    "name": student_folder.replace("_", " "),
                    "email": "N/A",
                    "phone": "N/A",
                    "course": "N/A"
                })
    return JSONResponse(students)

@app.post("/api/timer/start")
async def start_timer(request: Request):
    data = await request.json()
    duration = data.get("duration_minutes", 5)
    attendance_mgr.start_timer(duration)
    return JSONResponse({"status": "success", "message": f"Timer started for {duration} minutes"})

@app.post("/api/timer/stop")
async def stop_timer():
    attendance_mgr.stop_timer()
    return JSONResponse({"status": "success", "message": "Timer stopped"})

@app.get("/api/students")
async def get_students():
    return JSONResponse(attendance_mgr.get_summary())

# ─── WebSocket ───

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            sensors_raw = sensor_sim.read_sensors()
            frame_base64, vision_meta = vision_engine.process_frame()
            timer_state = attendance_mgr.get_timer_state()
            
            # Align with new React UI expectation (light -> light_level, add motion_detected)
            aligned_sensors = {
                "temperature": sensors_raw.get("temperature"),
                "humidity": sensors_raw.get("humidity"),
                "light_level": sensors_raw.get("light"),
                "aqi": sensors_raw.get("aqi"),
                "motion_detected": vision_meta.get("num_faces", 0) > 0,
                "status": sensors_raw.get("status")
            }
            
            payload = {
                "sensors": aligned_sensors,
                "vision": vision_meta,
                "frame": frame_base64,
                "timer": timer_state
            }
            
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.5) # Increased frequency slightly for "smooth" feel
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("WS Error:", e)

# ─── Serve Static Folder (plain HTML/CSS/JS) ───

STATIC_DIR = "static"

app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")

@app.get("/")
async def serve_index():
    index = os.path.join(STATIC_DIR, "index.html")
    with open(index, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/register")
async def serve_register():
    register = os.path.join(STATIC_DIR, "register.html")
    with open(register, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.on_event("startup")
async def startup_event():
    # Pre-warm vision engine
    pass

@app.on_event("shutdown")
def shutdown_event():
    vision_engine.release()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
