# Smart Classroom AI

A hardware + software system for automating classroom attendance, monitoring student attention, and controlling IoT devices using computer vision on a **Raspberry Pi 4GB**.

---

## 📁 Project Structure

```
smart-classroom/
├── frontend/                   # React + TypeScript + Vite dashboard (UI)
│   ├── src/
│   │   ├── pages/              # Dashboard, Attendance, Analytics, IoT, History, StudentRegistration
│   │   ├── components/         # Shared UI components
│   │   └── lib/api.ts          # Typed API client (connects to Flask backend)
│   ├── .env.example            # Copy to .env and set VITE_API_URL
│   └── package.json
│
├── backend/                    # Flask Python backend
│   ├── app/
│   │   ├── routes/             # students.py, attendance.py, analytics.py, iot.py
│   │   ├── services/           # face_recognition_service.py, attention_service.py, iot_service.py
│   │   ├── models/database.py  # SQLite schema + helpers
│   │   └── utils/camera.py     # Thread-safe OpenCV camera wrapper
│   ├── data/
│   │   ├── students/           # Registered student face images
│   │   └── sessions/           # SQLite database files
│   ├── run.py                  # Flask entry point
│   ├── config.py               # All configuration (reads from .env)
│   └── .env.example            # Copy to .env and configure
│
├── venv/                       # Python virtual environment (not committed)
├── requirements.txt            # Pinned Python dependencies
└── README.md
```

> **Note:** The existing `smart-class-dashboard-main` folder IS the `frontend/` — it has not been renamed to avoid breaking paths. Simply treat it as the frontend.

---

## 🚀 Quick Start

### 1. Backend Setup

```powershell
# Windows — activate venv
.\venv\Scripts\Activate.ps1

# Raspberry Pi / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
copy backend\.env.example backend\.env   # Windows
# cp backend/.env.example backend/.env  # Linux

# Start Flask server (from project root)
cd backend
python run.py
```

The backend will start at: `http://localhost:5000`  
Health check: `http://localhost:5000/api/health`

### 2. Frontend Setup

```powershell
cd "smart-class-dashboard-main"   # or frontend/ if you rename it

# Copy env
copy .env.example .env

# Install npm packages
npm install

# Start dev server
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/students/` | List all students |
| POST | `/api/students/` | Register student (multipart, with photo) |
| DELETE | `/api/students/:id` | Remove student |
| POST | `/api/attendance/sessions` | Start class session |
| PUT | `/api/attendance/sessions/:id/end` | End session |
| GET | `/api/attendance/sessions/:id/records` | Get attendance records |
| PUT | `/api/attendance/records/:id` | Override attendance status |
| GET | `/api/analytics/sessions/:id` | Attention analytics |
| GET | `/api/iot/status` | Device status |
| POST | `/api/iot/control` | Manual device control |

---

## 🍓 Raspberry Pi Deployment

1. Clone repo onto Pi
2. Create venv with Python 3.10: `python3.10 -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Install face recognition:
   ```bash
   sudo apt install -y libatlas-base-dev libhdf5-dev cmake build-essential
   pip install face-recognition
   ```
5. Uncomment `face-recognition` in `requirements.txt`
6. For GPIO: uncomment `RPi.GPIO` in `requirements.txt`, set `GPIO_ENABLED=true` in `.env`
7. Set your Pi's IP in frontend `.env`: `VITE_API_URL=http://<pi-ip>:5000`
8. Build frontend: `npm run build` and serve the `dist/` folder

---

## 🧩 Face Recognition (Windows Dev)

Face recognition requires `dlib` which needs CMake:

```powershell
pip install cmake
pip install dlib
pip install face-recognition
```

Then uncomment `face-recognition==1.3.0` in `requirements.txt`.

The backend starts fine **without** face-recognition installed — it logs a warning and skips face matching.

---

## 📡 IoT GPIO Wiring (Raspberry Pi)

| Device | GPIO Pin (BCM) | Default |
|--------|---------------|---------|
| Lights | 17 | Configurable in `.env` |
| Fans | 27 | Configurable in `.env` |

Set `GPIO_ENABLED=true` in `backend/.env` on the Pi.
