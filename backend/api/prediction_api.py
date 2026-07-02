from flask import Blueprint, request, jsonify, session
from backend.ml.predictor import TrafficPredictor
from backend.ml.route_engine import RouteEngine, resolve_location
from backend.services.prediction_service import save_prediction, get_user_predictions, get_prediction_count
from backend.utils.validators import validate_prediction
from backend.utils.datetime_utils import format_datetime
from datetime import datetime

prediction_bp = Blueprint('prediction_api', __name__, url_prefix='/api/predict')


def _prepare_prediction_input(data):
    source = data.get('source', '').strip()
    destination = data.get('destination', '').strip()
    city_name, _, _ = resolve_location(source)

    travel_date = data.get('travel_date', '')
    travel_time = data.get('travel_time', '12:00')
    try:
        dt = datetime.strptime(f'{travel_date} {travel_time}', '%Y-%m-%d %H:%M')
    except ValueError:
        dt = datetime.now()

    hour = dt.hour
    peak_hour = 1 if hour in range(7, 11) or hour in range(17, 21) else 0

    return {
        'source': source,
        'destination': destination,
        'city': city_name,
        'weather_condition': data.get('weather_condition', 'Clear'),
        'road_type': data.get('road_type', 'Highway'),
        'festival_indicator': int(data.get('festival_indicator', 0)),
        'peak_hour_indicator': peak_hour,
        'travel_date': travel_date,
        'travel_time': travel_time,
        'hour': hour,
        'day': dt.day,
        'month': dt.month,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'temperature': 28.0,
        'visibility': 8.0,
        'num_lanes': 3,
        'traffic_density': 55.0,
    }


@prediction_bp.route('', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json() or {}
    errors = validate_prediction(data)
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    try:
        pred_input = _prepare_prediction_input(data)
        predictor = TrafficPredictor()
        result = predictor.predict(pred_input)
        pred_id = save_prediction(session['user_id'], pred_input, result)
        result['prediction_id'] = pred_id

        route_engine = RouteEngine()
        route_data = route_engine.recommend(
            pred_input['source'],
            pred_input['destination'],
            {
                'weather_condition': pred_input['weather_condition'],
                'festival_indicator': pred_input['festival_indicator'],
                'peak_hour_indicator': pred_input['peak_hour_indicator'],
            }
        )
        best_route = next(
            (r for r in route_data['routes'] if r['route_name'] == route_data['recommended_route']),
            route_data['routes'][0]
        )
        result['route'] = {
            'recommended_route': route_data['recommended_route'],
            'source': best_route['source'],
            'destination': best_route['destination'],
            'waypoints': best_route['waypoints'],
            'distance_km': best_route['distance_km'],
            'estimated_time_min': best_route['estimated_time_min'],
            'explanation': route_data['explanation'],
        }
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@prediction_bp.route('/history', methods=['GET'])
def history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    limit = request.args.get('limit', 20, type=int)
    predictions = get_user_predictions(session['user_id'], limit)
    for p in predictions:
        p['created_at'] = format_datetime(p.get('created_at'))
    return jsonify({'success': True, 'predictions': predictions})


@prediction_bp.route('/count', methods=['GET'])
def count():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    cnt = get_prediction_count(session['user_id'])
    return jsonify({'success': True, 'count': cnt})
