import os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, send_file)
from models.database import (get_user_by_id, get_all_reports, get_report_by_id,
                              update_report_remarks, delete_report, get_doctor_stats,
                              save_prescription, get_prescription_by_report,
                              get_doctor_notifications, get_unread_notification_count,
                              mark_notification_read, mark_all_notifications_read)
from utils.pdf_generator import generate_pdf_report
from models.ml_model import get_feature_importance

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

REPORT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'reports')
os.makedirs(REPORT_FOLDER, exist_ok=True)


def doctor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'doctor':
            flash('Doctor access required.', 'warning')
            return redirect(url_for('auth.select_role'))
        return f(*args, **kwargs)
    return decorated


@doctor_bp.route('/dashboard')
@doctor_required
def dashboard():
    stats = get_doctor_stats()
    recent_rows = get_all_reports()[:10]
    recent_reports = [dict(r) for r in recent_rows]
    features, importance = get_feature_importance()
    notifications = get_doctor_notifications(session['user_id'], limit=10)
    unread_notif = get_unread_notification_count(session['user_id'])
    return render_template('doctor_dashboard.html',
                           stats=stats, reports=recent_reports,
                           features=features, importance=importance,
                           notifications=notifications, unread_notif=unread_notif,
                           now_hour=datetime.now().hour)


@doctor_bp.route('/notifications/mark-read', methods=['POST'])
@doctor_required
def mark_notifications_read():
    mark_all_notifications_read(session['user_id'])
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/notification/<int:notif_id>/view')
@doctor_required
def view_notification(notif_id):
    mark_notification_read(notif_id)
    # Redirect to the report
    from models.database import get_db
    conn = get_db()
    row = conn.execute('SELECT report_id FROM notifications WHERE id=?', (notif_id,)).fetchone()
    conn.close()
    if row:
        return redirect(url_for('doctor.report_detail', report_id=row['report_id']))
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/notifications')
@doctor_required
def notifications_page():
    notifications = get_doctor_notifications(session['user_id'], limit=50)
    unread_notif = get_unread_notification_count(session['user_id'])
    return render_template('doctor_notifications.html',
                           notifications=notifications, unread_notif=unread_notif)


@doctor_bp.route('/api/unread-count')
@doctor_required
def api_unread_count():
    from flask import jsonify as _jsonify
    count = get_unread_notification_count(session['user_id'])
    return _jsonify(count=count)


@doctor_bp.route('/patients')
@doctor_required
def patients():
    risk_filter = request.args.get('risk', 'all')
    date_filter = request.args.get('date', '')
    search = request.args.get('search', '').strip()
    reports = get_all_reports(
        risk_filter=risk_filter if risk_filter != 'all' else None,
        date_filter=date_filter if date_filter else None,
        search=search if search else None
    )
    unread_notif = get_unread_notification_count(session['user_id'])
    return render_template('doctor_patients.html',
                           reports=reports, risk_filter=risk_filter,
                           date_filter=date_filter, search=search,
                           unread_notif=unread_notif)


@doctor_bp.route('/report/<int:report_id>', methods=['GET', 'POST'])
@doctor_required
def report_detail(report_id):
    report = get_report_by_id(report_id)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('doctor.patients'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'remarks':
            remarks = request.form.get('remarks', '').strip()
            update_report_remarks(report_id, remarks)
            flash('Clinical remarks saved successfully.', 'success')
            return redirect(url_for('doctor.report_detail', report_id=report_id))
        elif action == 'prescription':
            medications = request.form.get('medications', '').strip()
            dosage = request.form.get('dosage', '').strip()
            instructions = request.form.get('instructions', '').strip()
            prevention = request.form.get('prevention', '').strip()
            follow_up = request.form.get('follow_up', '').strip()
            if not medications:
                flash('Please enter at least the medications.', 'danger')
            else:
                save_prescription(
                    report_id, report['user_id'], session['user_id'],
                    medications, dosage, instructions, prevention, follow_up
                )
                flash('Prescription sent to patient successfully.', 'success')
            return redirect(url_for('doctor.report_detail', report_id=report_id))
        elif action == 'delete':
            delete_report(report_id)
            flash('Report deleted.', 'info')
            return redirect(url_for('doctor.patients'))

    features, importance = get_feature_importance()
    existing_rx = get_prescription_by_report(report_id)
    unread_notif = get_unread_notification_count(session['user_id'])
    return render_template('doctor_report_detail.html',
                           report=report, features=features, importance=importance,
                           existing_rx=existing_rx, unread_notif=unread_notif)


@doctor_bp.route('/download-pdf/<int:report_id>')
@doctor_required
def download_pdf(report_id):
    report = get_report_by_id(report_id)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('doctor.patients'))

    pdf_filename = f"SmartHeart_{report['ref_id']}.pdf"
    pdf_path = os.path.join(REPORT_FOLDER, pdf_filename)
    ok, result = generate_pdf_report(dict(report), report['patient_name'], pdf_path)
    if not ok:
        flash('PDF generation failed.', 'danger')
        return redirect(url_for('doctor.report_detail', report_id=report_id))
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)
