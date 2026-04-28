"""
Students API — /api/students
Handles student registration, listing, and deletion.
Face images are saved to data/students/<id>.jpg
"""

import uuid
import os
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_db

students_bp = Blueprint("students", __name__)


def _student_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "roll": row["roll"],
        "imagePath": row["image_path"],
        "createdAt": row["created_at"],
    }


# ── GET /api/students ─────────────────────────────────────────────────────────
@students_bp.get("/")
def list_students():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM students ORDER BY created_at DESC"
    ).fetchall()
    return jsonify({"students": [_student_row_to_dict(r) for r in rows]})


# ── POST /api/students ────────────────────────────────────────────────────────
@students_bp.post("/")
def create_student():
    """
    Accepts multipart/form-data with fields:
        name (str), roll (str), photo (file, optional)
    """
    name = request.form.get("name", "").strip()
    roll = request.form.get("roll", "").strip()

    if not name or not roll:
        return jsonify({"error": "name and roll are required"}), 400

    db = get_db()

    # Check for duplicate roll number
    existing = db.execute(
        "SELECT id FROM students WHERE roll = ?", (roll,)
    ).fetchone()
    if existing:
        return jsonify({"error": f"Roll number '{roll}' already registered"}), 409

    student_id = str(uuid.uuid4())
    image_path = None

    # Save uploaded photo if provided
    photo = request.files.get("photo")
    if photo and photo.filename:
        students_dir = Path(current_app.config["STUDENTS_IMAGES_DIR"])
        ext = Path(photo.filename).suffix or ".jpg"
        filename = f"{student_id}{ext}"
        save_path = students_dir / filename
        photo.save(str(save_path))
        image_path = str(filename)

    db.execute(
        "INSERT INTO students (id, name, roll, image_path) VALUES (?, ?, ?, ?)",
        (student_id, name, roll, image_path),
    )
    db.commit()

    # TODO: Re-encode face embeddings after new student is added
    # from app.services.face_recognition_service import reload_embeddings
    # reload_embeddings()

    return jsonify({
        "message": f"{name} registered successfully",
        "student": {
            "id": student_id,
            "name": name,
            "roll": roll,
            "imagePath": image_path,
        }
    }), 201


# ── DELETE /api/students/<id> ─────────────────────────────────────────────────
@students_bp.delete("/<string:student_id>")
def delete_student(student_id: str):
    db = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Student not found"}), 404

    # Remove face image if it exists
    if row["image_path"]:
        img = Path(current_app.config["STUDENTS_IMAGES_DIR"]) / row["image_path"]
        if img.exists():
            os.remove(img)

    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()

    return jsonify({"message": f"Student '{row['name']}' removed"})


# ── PUT /api/students/<id> ────────────────────────────────────────────────────
@students_bp.put("/<string:student_id>")
def update_student(student_id: str):
    """Update name and/or roll number (not image)."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json(silent=True) or {}
    name = data.get("name", row["name"]).strip()
    roll = data.get("roll", row["roll"]).strip()

    db.execute(
        "UPDATE students SET name = ?, roll = ? WHERE id = ?",
        (name, roll, student_id),
    )
    db.commit()

    return jsonify({"message": "Student updated", "student": {"id": student_id, "name": name, "roll": roll}})
