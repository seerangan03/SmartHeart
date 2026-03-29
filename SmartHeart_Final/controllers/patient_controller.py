import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file)
from werkzeug.utils import secure_filename
from models.database import (get_user_by_id, get_patient_reports, save_report,
                              get_report_by_id, get_db, get_patient_prescriptions,
                              mark_prescription_read, get_unread_prescription_count,
                              create_notification, get_all_doctor_ids)
from models.ml_model import predict_risk, get_feature_importance
from utils.ocr_processor import analyze_scan_report
from utils.pdf_generator import generate_pdf_report

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
REPORT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'reports')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'patient':
            flash('Please log in as a patient.', 'warning')
            return redirect(url_for('auth.select_role'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@patient_bp.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    reports = get_patient_reports(session['user_id'])
    total = len(reports)
    high_risk = sum(1 for r in reports if r['severity'] in ('High', 'Critical'))
    latest = reports[0] if reports else None
    prescriptions = get_patient_prescriptions(session['user_id'])
    unread_rx = get_unread_prescription_count(session['user_id'])
    return render_template('patient_dashboard.html',
                           user=user, reports=reports[:5],
                           total=total, high_risk=high_risk, latest=latest,
                           prescriptions=prescriptions[:3], unread_rx=unread_rx)


@patient_bp.route('/assess', methods=['GET', 'POST'])
@login_required
def assess():
    """Manual input prediction — supports both normal POST and AJAX (X-Requested-With)."""
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        try:
            age         = int(request.form['age'])
            gender      = int(request.form['gender'])
            bp          = int(request.form['bp'])
            cholesterol = int(request.form['cholesterol'])
            heart_rate  = int(request.form['heart_rate'])
            sugar       = int(request.form['sugar'])
            chest_pain  = int(request.form['chest_pain'])

            if not (1 <= age <= 120):
                if is_ajax:
                    return jsonify(error='Please enter a valid age (1–120).'), 400
                flash('Please enter a valid age (1–120).', 'danger')
                return render_template('assess.html')

            risk_score, severity, explanation, color = predict_risk(
                age, gender, bp, cholesterol, heart_rate, sugar, chest_pain
            )
            ref_id = f"SH-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            data = dict(age=age, gender=gender, bp=bp, cholesterol=cholesterol,
                        heart_rate=heart_rate, sugar=sugar, chest_pain=chest_pain)
            save_report(session['user_id'], ref_id, data, risk_score, severity, 'manual')

            from models.database import get_db as _get_db
            conn = _get_db()
            report_row = conn.execute('SELECT id FROM reports WHERE ref_id=?', (ref_id,)).fetchone()
            conn.close()
            if report_row:
                msg = f"{session['user_name']} submitted a {severity} risk ({risk_score}%) manual assessment. Report: {ref_id}"
                for doctor_id in get_all_doctor_ids():
                    create_notification(doctor_id, session['user_id'], report_row['id'], msg)

            features, importance = get_feature_importance()
            report_id_val = report_row['id'] if report_row else None

            if is_ajax:
                return jsonify(
                    risk_score=risk_score, severity=severity,
                    explanation=explanation, color=color,
                    ref_id=ref_id, report_id=report_id_val,
                    features=features, importance=importance,
                    data=data
                )

            return render_template('result.html',
                                   risk_score=risk_score, severity=severity,
                                   explanation=explanation, color=color,
                                   data=data, ref_id=ref_id,
                                   report_id=report_id_val,
                                   features=features, importance=importance,
                                   unread_rx=get_unread_prescription_count(session['user_id']))
        except (ValueError, KeyError) as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(error=f'Invalid input: {str(e)}. Please check all fields.'), 400
            flash(f'Invalid input: {str(e)}. Please check all fields.', 'danger')
    return render_template('assess.html')


@patient_bp.route('/scan-upload', methods=['GET', 'POST'])
@login_required
def scan_upload():
    """Scan report upload and OCR-based prediction."""
    if request.method == 'POST':
        if 'scan' not in request.files:
            flash('No file uploaded.', 'danger')
            return render_template('scan_upload.html')

        file = request.files['scan']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return render_template('scan_upload.html')

        if not allowed_file(file.filename):
            flash('Unsupported file type. Please upload an image (PNG, JPG, etc.).', 'danger')
            return render_template('scan_upload.html')

        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # OCR returns complete data (uses clinical defaults for unreadable fields)
        data, raw_text, used_defaults = analyze_scan_report(filepath)

        # Show info if defaults were used
        if used_defaults:
            default_names = {'age': 'Age', 'gender': 'Gender', 'bp': 'Blood Pressure',
                             'cholesterol': 'Cholesterol', 'heart_rate': 'Heart Rate',
                             'sugar': 'Blood Sugar', 'chest_pain': 'Chest Pain'}
            names = ', '.join(default_names.get(f, f) for f in used_defaults)
            flash(f'OCR auto-filled {len(used_defaults)} field(s) with clinical defaults ({names}). Please verify the result.', 'info')

        risk_score, severity, explanation, color = predict_risk(
            data['age'], data['gender'], data['bp'], data['cholesterol'],
            data['heart_rate'], data['sugar'], data['chest_pain']
        )
        ref_id = f"SH-SCAN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        save_report(session['user_id'], ref_id, data, risk_score, severity, 'scan', filename)

        # Notify doctor
        from models.database import get_db as _get_db
        conn = _get_db()
        report_row = conn.execute('SELECT id FROM reports WHERE ref_id=?', (ref_id,)).fetchone()
        conn.close()
        if report_row:
            msg = f"{session['user_name']} uploaded a scan report with {severity} risk ({risk_score}%). Report: {ref_id}"
            for doctor_id in get_all_doctor_ids():
                create_notification(doctor_id, session['user_id'], report_row['id'], msg)

        features, importance = get_feature_importance()
        return render_template('result.html',
                               risk_score=risk_score, severity=severity,
                               explanation=explanation, color=color,
                               data=data, ref_id=ref_id,
                               report_id=report_row['id'] if report_row else None,
                               features=features, importance=importance,
                               unread_rx=get_unread_prescription_count(session['user_id']))

    return render_template('scan_upload.html')


@patient_bp.route('/prescriptions')
@login_required
def prescriptions():
    all_rx = get_patient_prescriptions(session['user_id'])
    return render_template('patient_prescriptions.html', prescriptions=all_rx)


@patient_bp.route('/prescription/<int:report_id>')
@login_required
def view_prescription(report_id):
    from models.database import get_prescription_by_report
    report = get_report_by_id(report_id)
    if not report or report['user_id'] != session['user_id']:
        flash('Prescription not found.', 'danger')
        return redirect(url_for('patient.dashboard'))
    rx = get_prescription_by_report(report_id)
    if not rx:
        flash('No prescription found for this report.', 'warning')
        return redirect(url_for('patient.dashboard'))
    mark_prescription_read(rx['id'])
    return render_template('prescription_view.html', rx=rx, report=report)


@patient_bp.route('/reports')
@login_required
def reports():
    all_reports = get_patient_reports(session['user_id'])
    unread_rx = get_unread_prescription_count(session['user_id'])
    return render_template('patient_reports.html', reports=all_reports, unread_rx=unread_rx)


@patient_bp.route('/download-pdf/<int:report_id>')
@login_required
def download_pdf(report_id):
    report = get_report_by_id(report_id)
    if not report or report['user_id'] != session['user_id']:
        flash('Report not found.', 'danger')
        return redirect(url_for('patient.reports'))

    pdf_filename = f"SmartHeart_{report['ref_id']}.pdf"
    pdf_path = os.path.join(REPORT_FOLDER, pdf_filename)

    ok, result = generate_pdf_report(dict(report), session['user_name'], pdf_path)
    if not ok:
        flash('PDF generation failed. ReportLab may not be installed.', 'danger')
        return redirect(url_for('patient.reports'))

    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)


@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_user_by_id(session['user_id'])
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        dob = request.form.get('dob', '')
        conn = get_db()
        conn.execute('UPDATE users SET name=?, phone=?, dob=? WHERE id=?',
                     (name, phone, dob, session['user_id']))
        conn.commit()
        conn.close()
        session['user_name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('patient.profile'))
    unread_rx = get_unread_prescription_count(session['user_id'])
    return render_template('patient_profile.html', user=user, unread_rx=unread_rx)
