import os
from datetime import datetime
import threading
import time

class AttendanceManager:
    def __init__(self, dataset_path="dataset"):
        self.dataset_path = dataset_path
        self.roster = {}
        
        # Timer fields
        self.timer_running = False
        self.timer_duration = 300  # seconds (5 min default)
        self.timer_remaining = 0
        self.timer_start_time = None
        self._timer_thread = None
        
        self.load_roster()

    def load_roster(self):
        """Scans the dataset folder and registers all known students as Absent"""
        self.roster = {}
        if not os.path.exists(self.dataset_path):
            os.makedirs(self.dataset_path, exist_ok=True)
            return
            
        for student_name in os.listdir(self.dataset_path):
            student_dir = os.path.join(self.dataset_path, student_name)
            if os.path.isdir(student_dir):
                self.roster[student_name] = {
                    "name": student_name,
                    "status": "Absent",
                    "check_in_time": "--:--",
                    "distraction_score": 0
                }

    def start_timer(self, duration_minutes=5):
        """Start the attendance window timer"""
        self.timer_duration = duration_minutes * 60
        self.timer_remaining = self.timer_duration
        self.timer_start_time = time.time()
        self.timer_running = True
        
        # Reset all to Absent when starting a new session
        for name in self.roster:
            self.roster[name]["status"] = "Absent"
            self.roster[name]["check_in_time"] = "--:--"
            self.roster[name]["distraction_score"] = 0
        
        # Background countdown thread
        if self._timer_thread and self._timer_thread.is_alive():
            return
        self._timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self._timer_thread.start()

    def _run_timer(self):
        while self.timer_running and self.timer_remaining > 0:
            time.sleep(1)
            elapsed = time.time() - self.timer_start_time
            self.timer_remaining = max(0, self.timer_duration - elapsed)
            
        if self.timer_remaining <= 0:
            self.timer_running = False
            # Mark everyone still Absent who was never seen — they stay Absent
            # This is already the default state. Timer simply stops.

    def stop_timer(self):
        self.timer_running = False
        self.timer_remaining = 0

    def get_timer_state(self):
        return {
            "running": self.timer_running,
            "duration": self.timer_duration,
            "remaining": round(self.timer_remaining, 0)
        }

    def mark_seen(self, student_name, phone_detected=False):
        if student_name not in self.roster:
            self.add_new_student(student_name)

        student = self.roster[student_name]
        
        if student["status"] == "Absent":
            now = datetime.now()
            student["check_in_time"] = now.strftime("%H:%M:%S")
            
            if self.timer_running:
                # Timer is running → mark Present
                student["status"] = "Present"
            else:
                # Timer has expired or was never started → mark Late
                student["status"] = "Late"
                
        if phone_detected:
            student["distraction_score"] += 1

    def get_summary(self):
        return list(self.roster.values())
        
    def add_new_student(self, name):
        self.roster[name] = {
            "name": name,
            "status": "Absent",
            "check_in_time": "--:--",
            "distraction_score": 0
        }
