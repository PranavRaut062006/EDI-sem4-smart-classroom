"""
Smart Classroom AI — Flask Backend Entry Point
Run:  python run.py
      or: flask --app run run --host=0.0.0.0 --port=5000
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # host="0.0.0.0" makes it accessible on the local network (Raspberry Pi)
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
