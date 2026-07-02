import re
from functools import wraps
from flask import session, jsonify, redirect, url_for, request


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('pages.login'))
        return f(*args, **kwargs)
    return decorated


def validate_registration(data):
    errors = []
    if not data.get('username') or len(data['username']) < 3:
        errors.append('Username must be at least 3 characters')
    if not data.get('email') or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
        errors.append('Valid email address is required')
    if not data.get('password') or len(data['password']) < 6:
        errors.append('Password must be at least 6 characters')
    phone = data.get('phone_number', '').strip()
    if phone and not re.match(r'^[6-9][0-9]{9}$', phone):
        errors.append('Phone number must be a valid 10-digit Indian mobile number')
    return errors


def validate_prediction(data):
    errors = []
    required = ['source', 'destination', 'weather_condition', 'road_type', 'travel_date', 'travel_time']
    for field in required:
        if not data.get(field):
            errors.append(f'{field.replace("_", " ").title()} is required')
    return errors
