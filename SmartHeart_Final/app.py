import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, redirect, url_for
from models.database import init_db
from models.ml_model import load_model
from controllers.auth_controller import auth_bp
from controllers.patient_controller import patient_bp
from controllers.doctor_controller import doctor_bp

app = Flask(__name__)
app.secret_key = 'smartheart-secret-key-2024-medical-system'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize DB and ML model at app startup (not just when run directly)
with app.app_context():
    init_db()
    load_model()

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)


@app.route('/')
def index():
    return redirect(url_for('auth.select_role'))


@app.errorhandler(404)
def not_found(e):
    return "<h2>404 - Page not found</h2><a href='/'>Go Home</a>", 404


@app.errorhandler(413)
def file_too_large(e):
    return "<h2>File too large. Maximum size is 16MB.</h2>", 413


if __name__ == '__main__':
    print("=" * 60)
    print("  SmartHeart - Initializing...")
    print("=" * 60)

    # Initialize database
    print("[DB] Initializing database...")
    init_db()

    # Pre-load/train ML model
    print("[ML] Loading prediction model...")
    load_model()

    print("[OK] System ready!")
    print("[INFO] Default doctor login: doctor@smartheart.com / Doctor@123")
    print("[INFO] Running at: http://127.0.0.1:5000")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
