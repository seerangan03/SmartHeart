from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import get_user_by_email, create_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/select-role')
def select_role():
    """Landing page — role selection."""
    session.clear()
    return render_template('select_role.html')


@auth_bp.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    """Login/Register page for a given role."""
    if role not in ('doctor', 'patient'):
        return redirect(url_for('auth.select_role'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = get_user_by_email(email)

            if not user:
                flash('No account found with that email.', 'danger')
            elif user['role'] != role:
                flash(f'This account is not registered as a {role}.', 'danger')
            elif not check_password_hash(user['password'], password):
                flash('Incorrect password. Please try again.', 'danger')
            else:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                session['user_email'] = user['email']
                flash(f"Welcome back, {user['name']}!", 'success')
                if role == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                return redirect(url_for('patient.dashboard'))

        elif action == 'register':
            name = request.form.get('reg_name', '').strip()
            email = request.form.get('reg_email', '').strip().lower()
            password = request.form.get('reg_password', '')
            confirm = request.form.get('reg_confirm', '')
            phone = request.form.get('reg_phone', '').strip()
            dob = request.form.get('reg_dob', '')
            gender = request.form.get('reg_gender', '')

            if not name or not email or not password:
                flash('Please fill in all required fields.', 'danger')
            elif len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
            elif password != confirm:
                flash('Passwords do not match.', 'danger')
            else:
                pw_hash = generate_password_hash(password)
                ok, msg = create_user(name, email, pw_hash, role, phone, dob, gender)
                if ok:
                    flash('Account created! Please log in.', 'success')
                else:
                    flash(msg, 'danger')

    return render_template('login.html', role=role)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.select_role'))
