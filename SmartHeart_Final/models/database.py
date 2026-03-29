"""
SmartHeart - Database Models
Handles all SQLite database operations
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'smartheart.db')


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database with all required tables and seed data."""
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('doctor','patient')),
            phone TEXT,
            dob TEXT,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Reports table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ref_id TEXT UNIQUE NOT NULL,
            age INTEGER,
            gender TEXT,
            bp INTEGER,
            cholesterol INTEGER,
            heart_rate INTEGER,
            sugar INTEGER,
            chest_pain INTEGER,
            risk_score REAL,
            severity TEXT,
            doctor_remarks TEXT,
            input_method TEXT DEFAULT 'manual',
            scan_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Prescriptions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            medications TEXT,
            dosage TEXT,
            instructions TEXT,
            prevention TEXT,
            follow_up TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id),
            FOREIGN KEY (patient_id) REFERENCES users(id),
            FOREIGN KEY (doctor_id) REFERENCES users(id)
        )
    ''')

    # Notifications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            report_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES users(id),
            FOREIGN KEY (patient_id) REFERENCES users(id),
            FOREIGN KEY (report_id) REFERENCES reports(id)
        )
    ''')

    # Seed default doctor account
    from werkzeug.security import generate_password_hash
    c.execute("SELECT id FROM users WHERE email = 'doctor@smartheart.com'")
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (name, email, password, role, phone, gender)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'Dr. Sarah Mitchell',
            'doctor@smartheart.com',
            generate_password_hash('Doctor@123'),
            'doctor',
            '+1-800-555-0100',
            'Female'
        ))

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def create_user(name, email, password_hash, role, phone='', dob='', gender=''):
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO users (name, email, password, role, phone, dob, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, password_hash, role, phone, dob, gender))
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()


def save_report(user_id, ref_id, data, risk_score, severity, input_method='manual', scan_filename=''):
    conn = get_db()
    conn.execute('''
        INSERT INTO reports (user_id, ref_id, age, gender, bp, cholesterol, heart_rate, sugar,
                             chest_pain, risk_score, severity, input_method, scan_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, ref_id,
        data.get('age'), data.get('gender'), data.get('bp'),
        data.get('cholesterol'), data.get('heart_rate'), data.get('sugar'),
        data.get('chest_pain'), risk_score, severity, input_method, scan_filename
    ))
    conn.commit()
    conn.close()


def get_patient_reports(user_id):
    conn = get_db()
    reports = conn.execute('''
        SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return reports


def get_all_reports(risk_filter=None, date_filter=None, search=None):
    conn = get_db()
    query = '''
        SELECT r.*, u.name as patient_name, u.email as patient_email
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE u.role = 'patient'
    '''
    params = []
    if risk_filter and risk_filter != 'all':
        query += ' AND r.severity = ?'
        params.append(risk_filter)
    if date_filter:
        query += ' AND DATE(r.created_at) = ?'
        params.append(date_filter)
    if search:
        query += ' AND (u.name LIKE ? OR u.email LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    query += ' ORDER BY r.created_at DESC'
    reports = conn.execute(query, params).fetchall()
    conn.close()
    return reports


def get_report_by_id(report_id):
    conn = get_db()
    report = conn.execute('''
        SELECT r.*, u.name as patient_name, u.email as patient_email
        FROM reports r JOIN users u ON r.user_id = u.id
        WHERE r.id = ?
    ''', (report_id,)).fetchone()
    conn.close()
    return report


def update_report_remarks(report_id, remarks):
    conn = get_db()
    conn.execute('UPDATE reports SET doctor_remarks = ? WHERE id = ?', (remarks, report_id))
    conn.commit()
    conn.close()


def delete_report(report_id):
    conn = get_db()
    conn.execute('DELETE FROM reports WHERE id = ?', (report_id,))
    conn.commit()
    conn.close()


def get_doctor_stats():
    conn = get_db()
    total_patients = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'patient'"
    ).fetchone()[0]
    high_risk = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE severity IN ('High', 'Critical')"
    ).fetchone()[0]
    total_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    recent_reports = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE DATE(created_at) = DATE('now')"
    ).fetchone()[0]
    conn.close()
    return {
        'total_patients': total_patients,
        'high_risk': high_risk,
        'total_reports': total_reports,
        'recent_reports': recent_reports
    }


def save_prescription(report_id, patient_id, doctor_id, medications, dosage, instructions, prevention, follow_up):
    conn = get_db()
    # Check if prescription already exists for this report
    existing = conn.execute('SELECT id FROM prescriptions WHERE report_id = ?', (report_id,)).fetchone()
    if existing:
        conn.execute('''
            UPDATE prescriptions SET medications=?, dosage=?, instructions=?, prevention=?, follow_up=?,
            doctor_id=?, is_read=0, created_at=CURRENT_TIMESTAMP WHERE report_id=?
        ''', (medications, dosage, instructions, prevention, follow_up, doctor_id, report_id))
    else:
        conn.execute('''
            INSERT INTO prescriptions (report_id, patient_id, doctor_id, medications, dosage, instructions, prevention, follow_up)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (report_id, patient_id, doctor_id, medications, dosage, instructions, prevention, follow_up))
    conn.commit()
    conn.close()


def get_prescription_by_report(report_id):
    conn = get_db()
    rx = conn.execute('''
        SELECT p.*, u.name as doctor_name FROM prescriptions p
        JOIN users u ON p.doctor_id = u.id WHERE p.report_id = ?
    ''', (report_id,)).fetchone()
    conn.close()
    return rx


def get_patient_prescriptions(patient_id):
    conn = get_db()
    rxs = conn.execute('''
        SELECT p.*, u.name as doctor_name, r.ref_id, r.severity, r.risk_score
        FROM prescriptions p
        JOIN users u ON p.doctor_id = u.id
        JOIN reports r ON p.report_id = r.id
        WHERE p.patient_id = ?
        ORDER BY p.created_at DESC
    ''', (patient_id,)).fetchall()
    conn.close()
    return rxs


def mark_prescription_read(prescription_id):
    conn = get_db()
    conn.execute('UPDATE prescriptions SET is_read = 1 WHERE id = ?', (prescription_id,))
    conn.commit()
    conn.close()


def get_unread_prescription_count(patient_id):
    conn = get_db()
    count = conn.execute(
        'SELECT COUNT(*) FROM prescriptions WHERE patient_id = ? AND is_read = 0', (patient_id,)
    ).fetchone()[0]
    conn.close()
    return count


def create_notification(doctor_id, patient_id, report_id, message):
    conn = get_db()
    conn.execute('''
        INSERT INTO notifications (doctor_id, patient_id, report_id, message)
        VALUES (?, ?, ?, ?)
    ''', (doctor_id, patient_id, report_id, message))
    conn.commit()
    conn.close()


def get_doctor_notifications(doctor_id, limit=20):
    conn = get_db()
    rows = conn.execute('''
        SELECT n.*, u.name as patient_name, r.ref_id, r.severity, r.risk_score, r.input_method
        FROM notifications n
        JOIN users u ON n.patient_id = u.id
        JOIN reports r ON n.report_id = r.id
        WHERE n.doctor_id = ?
        ORDER BY n.created_at DESC
        LIMIT ?
    ''', (doctor_id, limit)).fetchall()
    conn.close()
    return rows


def get_unread_notification_count(doctor_id):
    conn = get_db()
    count = conn.execute(
        'SELECT COUNT(*) FROM notifications WHERE doctor_id = ? AND is_read = 0', (doctor_id,)
    ).fetchone()[0]
    conn.close()
    return count


def mark_notification_read(notification_id):
    conn = get_db()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notification_id,))
    conn.commit()
    conn.close()


def mark_all_notifications_read(doctor_id):
    conn = get_db()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE doctor_id = ?', (doctor_id,))
    conn.commit()
    conn.close()


def get_default_doctor_id():
    """Return the ID of the first/default doctor account."""
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE role='doctor' LIMIT 1").fetchone()
    conn.close()
    return row['id'] if row else None


def get_all_doctor_ids():
    """Return list of IDs of all registered doctor accounts."""
    conn = get_db()
    rows = conn.execute("SELECT id FROM users WHERE role='doctor'").fetchall()
    conn.close()
    return [r['id'] for r in rows]
