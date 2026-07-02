from flask import Blueprint, request, jsonify, session
from backend.ml.route_engine import RouteEngine
from backend.services.route_service import (
    save_travel_history, get_travel_history,
    save_route, get_saved_routes, delete_saved_route,
    delete_travel_history_item, clear_travel_history
)
from backend.services.auth_service import get_user_profile
from backend.utils.datetime_utils import format_datetime

route_bp = Blueprint('route_api', __name__, url_prefix='/api/route')


@route_bp.route('/recommend', methods=['POST'])
def recommend():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json() or {}
    source = data.get('source', '').strip()
    destination = data.get('destination', '').strip()

    if not source or not destination:
        return jsonify({'success': False, 'message': 'Source and destination are required'}), 400

    context = {
        'weather_condition': data.get('weather_condition', 'Clear'),
        'temperature': float(data.get('temperature', 28)),
        'visibility': float(data.get('visibility', 8)),
        'festival_indicator': int(data.get('festival_indicator', 0)),
        'peak_hour_indicator': int(data.get('peak_hour_indicator', 1)),
    }

    user = get_user_profile(session['user_id'])
    if user:
        context['route_preference'] = user.get('route_preference') or 'fastest'

    try:
        engine = RouteEngine()
        result = engine.recommend(source, destination, context)
        result['weather_condition'] = context['weather_condition']
        save_travel_history(session['user_id'], result, result['recommended_route'])
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@route_bp.route('/history', methods=['GET'])
def history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    rows = get_travel_history(session['user_id'])
    for r in rows:
        r['travel_date'] = format_datetime(r.get('travel_date'))
    return jsonify({'success': True, 'history': rows})


@route_bp.route('/history/<int:history_id>', methods=['DELETE'])
def delete_history_item(history_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    if delete_travel_history_item(session['user_id'], history_id):
        return jsonify({'success': True, 'message': 'History deleted'})
    return jsonify({'success': False, 'message': 'History item not found'}), 404


@route_bp.route('/history', methods=['DELETE'])
def clear_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    deleted = clear_travel_history(session['user_id'])
    return jsonify({'success': True, 'message': f'Cleared {deleted} items'})


@route_bp.route('/save', methods=['POST'])
def save():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    data = request.get_json() or {}
    if not data.get('source') or not data.get('destination'):
        return jsonify({'success': False, 'message': 'Source and destination required'}), 400
    route_id = save_route(session['user_id'], data)
    return jsonify({'success': True, 'route_id': route_id, 'message': 'Route saved'})


@route_bp.route('/saved', methods=['GET'])
def saved():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    routes = get_saved_routes(session['user_id'])
    for r in routes:
        r['created_at'] = format_datetime(r.get('created_at'))
        r['last_used'] = format_datetime(r.get('last_used'))
    return jsonify({'success': True, 'routes': routes})


@route_bp.route('/saved/<int:route_id>', methods=['DELETE'])
def delete_route(route_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    if delete_saved_route(session['user_id'], route_id):
        return jsonify({'success': True, 'message': 'Route deleted'})
    return jsonify({'success': False, 'message': 'Route not found'}), 404
