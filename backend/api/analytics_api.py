from flask import Blueprint, request, jsonify, session
from backend.services.analytics_service import get_heatmap_data
import urllib.request
import json as _json

analytics_bp = Blueprint('analytics_api', __name__, url_prefix='/api/analytics')

# Fallback: map small/unknown Indian cities → nearest major city for geocoding
CITY_ALIAS = {
    'murbad': 'Thane', 'badlapur': 'Thane', 'ambernath': 'Thane',
    'ulhasnagar': 'Thane', 'dombivli': 'Thane', 'kalyan': 'Thane',
    'panvel': 'Navi Mumbai', 'khopoli': 'Pune', 'lonavala': 'Pune',
    'khandala': 'Pune', 'karjat': 'Pune', 'kasara': 'Nashik',
    'igatpuri': 'Nashik', 'Manor': 'Mumbai',
}


@analytics_bp.route('/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city', '').strip()
    if not city:
        return jsonify({'success': False, 'message': 'City required'}), 400

    lookup = CITY_ALIAS.get(city.lower(), city)
    weather, desc = None, None

    # Try live weather (Open-Meteo, short timeout + SSL bypass for Windows compat)
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        geo_url = (f'https://geocoding-api.open-meteo.com/v1/search'
                   f'?name={urllib.request.quote(lookup)}&count=1&language=en&format=json')
        req = urllib.request.Request(geo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=3) as r:
            geo = _json.loads(r.read())

        if geo.get('results'):
            lat = geo['results'][0]['latitude']
            lon = geo['results'][0]['longitude']
            wx_url = (f'https://api.open-meteo.com/v1/forecast'
                      f'?latitude={lat}&longitude={lon}&current_weather=true')
            req2 = urllib.request.Request(wx_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2, context=ctx, timeout=3) as r2:
                wx = _json.loads(r2.read())
            code = int(wx.get('current_weather', {}).get('weathercode', 0))
            weather = _map_weather_code(code)
            desc = f'Live — WMO {code}'
    except Exception:
        pass  # Fall through to seasonal estimate

    # Seasonal fallback — accurate for Indian cities
    if not weather:
        weather, desc = _seasonal_weather(lookup)

    return jsonify({
        'success': True,
        'weather': weather,
        'city': lookup,
        'description': desc,
        'source': 'live' if desc and desc.startswith('Live') else 'seasonal'
    })


def _seasonal_weather(city=''):
    """Return season-appropriate weather for Indian cities."""
    import datetime
    month = datetime.datetime.now().month
    city_l = city.lower()

    if 6 <= month <= 9:
        return 'Rain', 'Monsoon season — rain expected'
    elif 10 <= month <= 11:
        return 'Cloudy', 'Post-monsoon — mostly cloudy'
    elif month in (12, 1, 2):
        northern = any(c in city_l for c in [
            'delhi', 'chandigarh', 'lucknow', 'jaipur', 'agra',
            'amritsar', 'ludhiana', 'meerut', 'varanasi', 'patna'
        ])
        return ('Fog', 'Winter fog (north India)') if northern else ('Clear', 'Clear winter sky')
    else:  # March – May
        return 'Haze', 'Summer heat haze'


def _map_weather_code(code):
    if code == 0:        return 'Clear'
    if code <= 3:        return 'Cloudy'
    if code <= 48:       return 'Fog'
    if code <= 67:       return 'Rain'
    if code <= 77:       return 'Cloudy'
    if code <= 82:       return 'Rain'
    if code >= 95:       return 'Storm'
    return 'Cloudy'


@analytics_bp.route('/heatmap', methods=['GET'])
def heatmap():
    data = get_heatmap_data()
    return jsonify({'success': True, 'heatmap': data})


@analytics_bp.route('/feedback', methods=['POST'])
def feedback():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    from backend.extensions import mysql
    data = request.get_json() or {}
    rating = int(data.get('rating', 3))
    cur = mysql.connection.cursor()
    cur.execute('''
        INSERT INTO Feedback (user_id, prediction_id, rating, comment, feedback_type)
        VALUES (%s, %s, %s, %s, %s)
    ''', (
        session['user_id'], data.get('prediction_id'),
        rating, data.get('comment', ''), data.get('feedback_type', 'general')
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True, 'message': 'Feedback submitted'})


@analytics_bp.route('/weekly-report', methods=['GET'])
def weekly_report():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    from backend.extensions import mysql as db
    try:
        cur = db.connection.cursor()

        cur.execute('''
            SELECT DATE(created_at) AS date,
                   COUNT(*) AS total,
                   SUM(predicted_congestion = 'Low')    AS low_count,
                   SUM(predicted_congestion = 'Medium') AS medium_count,
                   SUM(predicted_congestion = 'High')   AS high_count
            FROM Predictions
            WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        ''', (session['user_id'],))
        daily_data = cur.fetchall()
        for row in daily_data:
            row['date']         = str(row['date'])
            row['total']        = int(row['total'] or 0)
            row['low_count']    = int(row['low_count'] or 0)
            row['medium_count'] = int(row['medium_count'] or 0)
            row['high_count']   = int(row['high_count'] or 0)

        cur.execute('''
            SELECT source_location, destination_location, COUNT(*) AS count
            FROM Predictions
            WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY source_location, destination_location
            ORDER BY count DESC LIMIT 5
        ''', (session['user_id'],))
        top_routes = cur.fetchall()

        cur.execute('''
            SELECT predicted_congestion, COUNT(*) AS count
            FROM Predictions
            WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY predicted_congestion
        ''', (session['user_id'],))
        congestion_distribution = cur.fetchall()

        cur.close()
        return jsonify({
            'success': True,
            'daily_data': daily_data,
            'top_routes': top_routes,
            'congestion_distribution': congestion_distribution
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
