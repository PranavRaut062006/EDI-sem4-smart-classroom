"""
Analytics API — /api/analytics
Returns per-student attention and phone detection data for a session.
"""

from flask import Blueprint, request, jsonify
from app.models.database import get_db

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/sessions/<string:session_id>")
def get_session_analytics(session_id: str):
    """
    Return attention % and phone count per student for a given session.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT an.*, s.name, s.roll
        FROM analytics an
        JOIN students s ON s.id = an.student_id
        WHERE an.session_id = ?
        ORDER BY an.attention_pct DESC
        """,
        (session_id,),
    ).fetchall()

    if not rows:
        return jsonify({"analytics": [], "summary": {
            "avgAttention": 0,
            "totalPhoneEvents": 0,
            "lowAttentionCount": 0,
            "trackedCount": 0,
        }})

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
    avg_attention = round(sum(d["attentionPct"] for d in data) / total) if total else 0
    total_phones = sum(d["phoneCount"] for d in data)
    low_attention = sum(1 for d in data if d["attentionPct"] < 50)

    return jsonify({
        "analytics": data,
        "summary": {
            "avgAttention": avg_attention,
            "totalPhoneEvents": total_phones,
            "lowAttentionCount": low_attention,
            "trackedCount": total,
        },
    })


@analytics_bp.put("/sessions/<string:session_id>/students/<string:student_id>")
def update_analytics(session_id: str, student_id: str):
    """
    Update or create analytics record for a student in a session.
    Called internally by the attention monitoring service.
    Body: { attentionPct: int, phoneCount: int }
    """
    import uuid
    from datetime import datetime

    data = request.get_json(silent=True) or {}
    attention_pct = int(data.get("attentionPct", 0))
    phone_count = int(data.get("phoneCount", 0))
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    db = get_db()

    existing = db.execute(
        "SELECT id FROM analytics WHERE session_id = ? AND student_id = ?",
        (session_id, student_id),
    ).fetchone()

    if existing:
        db.execute(
            """UPDATE analytics SET attention_pct = ?, phone_count = ?, updated_at = ?
               WHERE session_id = ? AND student_id = ?""",
            (attention_pct, phone_count, now, session_id, student_id),
        )
    else:
        db.execute(
            """INSERT INTO analytics (id, session_id, student_id, attention_pct, phone_count, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), session_id, student_id, attention_pct, phone_count, now),
        )

    db.commit()
    return jsonify({"message": "Analytics updated"})
