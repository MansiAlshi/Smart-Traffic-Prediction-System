from flask import Blueprint, request, jsonify, session
from backend.services.auth_service import register_user, authenticate_user, get_user_profile, update_user_profile
from backend.utils.validators import validate_registration
from backend.utils.datetime_utils import format_datetime

auth_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json() or request.form
        errors = validate_registration(data)
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        user_id, error = register_user(
            data['username'], data['email'], data['password'],
            data.get('full_name', ''), data.get('city', 'Mumbai'),
            data.get('phone_number', '')
        )
        if error:
            return jsonify({'success': False, 'message': error}), 409

        return jsonify({'success': True, 'message': 'Registration successful', 'user_id': user_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or request.form
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    user, error = authenticate_user(username, password)
    if error:
        return jsonify({'success': False, 'message': error}), 401

    session.permanent = True
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['full_name'] = user['full_name'] or user['username']

    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'city': user['city'],
        }
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@auth_bp.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    user = get_user_profile(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    user['created_at'] = format_datetime(user.get('created_at'))
    user['last_login'] = format_datetime(user.get('last_login'))
    return jsonify({'success': True, 'user': user})


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    data = request.get_json() or {}
    update_user_profile(
        session['user_id'],
        data.get('full_name', ''),
        data.get('city', 'Mumbai'),
        data.get('email', ''),
        data.get('phone_number', ''),
        data.get('route_preference', 'fastest'),
    )
    return jsonify({'success': True, 'message': 'Profile updated'})


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    data = request.get_json() or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    if not current_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Both fields are required'}), 400
    if len(new_pw) < 6:
        return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400
    from backend.services.auth_service import change_user_password
    ok, msg = change_user_password(session['user_id'], current_pw, new_pw)
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@auth_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    from backend.services.auth_service import delete_user
    ok, msg = delete_user(session['user_id'])
    if ok:
        session.clear()
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 400)


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
    from backend.services.auth_service import check_email_exists
    exists = check_email_exists(email)
    # Always return success to prevent email enumeration
    return jsonify({
        'success': True,
        'message': 'If this email exists in our system, reset instructions have been noted. (Email sending not configured — contact support to reset your password.)'
    })
