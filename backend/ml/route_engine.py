import json
import math
import random
import urllib.parse
import urllib.request
from backend.ml.predictor import TrafficPredictor
from backend.ml.osrm_client import fetch_driving_routes

CITY_COORDS = {
    'Mumbai': (19.0760, 72.8777),
    'Delhi': (28.6139, 77.2090),
    'Bangalore': (12.9716, 77.5946),
    'Hyderabad': (17.3850, 78.4867),
    'Chennai': (13.0827, 80.2707),
    'Kolkata': (22.5726, 88.3639),
    'Pune': (18.5204, 73.8567),
    'Ahmedabad': (23.0225, 72.5714),
    'Jaipur': (26.9124, 75.7873),
    'Lucknow': (26.8467, 80.9462),
    'Chandigarh': (30.7333, 76.7794),
    'Kochi': (9.9312, 76.2673),
    'Indore': (22.7196, 75.8577),
    'Bhopal': (23.2599, 77.4126),
    'Nagpur': (21.1458, 79.0882),
    'Surat': (21.1702, 72.8311),
    'Visakhapatnam': (17.6868, 83.2185),
    'Patna': (25.5941, 85.1376),
    'Varanasi': (25.3176, 82.9739),
    'Agra': (27.1767, 78.0081),
    'Kalyan': (19.2437, 73.1355),
    'Murbad': (19.2544, 73.3969),
    'Thane': (19.2183, 72.9781),
    'Navi Mumbai': (19.0330, 73.0297),
    'Dombivli': (19.2167, 73.0833),
    'Ambernath': (19.2094, 73.1860),
    'Badlapur': (19.1557, 73.2655),
    'Ulhasnagar': (19.2215, 73.1645),
    'Vasai': (19.3919, 72.8397),
    'Virar': (19.4559, 72.8110),
    'Lonavala': (18.7508, 73.4055),
    'Nashik': (19.9975, 73.7898),
}

_GEOCODE_CACHE = {}
ROUTE_VARIANTS = [
    {'name': 'Route A', 'modifier': 1.0, 'road_type': 'Highway', 'lanes': 4, 'label': 'Fastest'},
    {'name': 'Route B', 'modifier': 1.15, 'road_type': 'Urban', 'lanes': 3, 'label': 'Balanced'},
    {'name': 'Route C', 'modifier': 1.3, 'road_type': 'Suburban', 'lanes': 2, 'label': 'Scenic'},
]

CONGESTION_SCORE = {'Low': 1, 'Medium': 2, 'High': 3}
RISK_SCORE = {'Low': 1, 'Medium': 2, 'High': 3}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def resolve_location_cached(name):
    """Fast check for cached location. Returns (name, lat, lng) or None. Thread-safe."""
    key = name.strip().lower()
    
    # 1. Preset cities
    for city, coords in CITY_COORDS.items():
        if city.lower() == key:
            return city, coords[0], coords[1]
            
    # 2. In-memory cache
    if key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[key]
        
    # 3. Database cache
    try:
        from flask import current_app
        if current_app:
            from backend.extensions import mysql
            cur = mysql.connection.cursor()
            cur.execute(
                'SELECT resolved_name, lat, lng FROM Geocode_Cache WHERE query_text = %s',
                (key,)
            )
            row = cur.fetchone()
            cur.close()
            if row:
                resolved_name = row['resolved_name']
                lat = float(row['lat'])
                lng = float(row['lng'])
                _GEOCODE_CACHE[key] = (resolved_name, lat, lng)
                return _GEOCODE_CACHE[key]
    except Exception:
        pass
        
    return None


def geocode_api_call(name):
    """Makes Nominatim HTTP call directly. Returns (resolved_name, lat, lng) or None. Thread-safe."""
    query = urllib.parse.urlencode({
        'q': f'{name.strip()}, India',
        'format': 'json',
        'limit': 1,
    })
    req = urllib.request.Request(
        f'https://nominatim.openstreetmap.org/search?{query}',
        headers={'User-Agent': 'SmartTrafficAI/1.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            results = json.loads(resp.read().decode())
        if results:
            lat = float(results[0]['lat'])
            lng = float(results[0]['lon'])
            resolved_name = name.strip().title()
            return resolved_name, lat, lng
    except Exception:
        pass
    return None


def resolve_location(name):
    """Resolves location sequentially. Main thread safe."""
    cached = resolve_location_cached(name)
    if cached:
        return cached

    # Call API if uncached
    res = geocode_api_call(name)
    if res:
        key = name.strip().lower()
        resolved_name, lat, lng = res
        _GEOCODE_CACHE[key] = (resolved_name, lat, lng)
        try:
            from flask import current_app
            if current_app:
                from backend.extensions import mysql
                cur = mysql.connection.cursor()
                cur.execute(
                    'INSERT INTO Geocode_Cache (query_text, resolved_name, lat, lng) VALUES (%s, %s, %s, %s) '
                    'ON DUPLICATE KEY UPDATE resolved_name = VALUES(resolved_name), lat = VALUES(lat), lng = VALUES(lng)',
                    (key, resolved_name, lat, lng)
                )
                mysql.connection.commit()
                cur.close()
        except Exception:
            pass
        return resolved_name, lat, lng

    # Fallback to substring match for preset cities if geocoding fails
    query = name.strip().lower()
    for city, coords in CITY_COORDS.items():
        city_lower = city.lower()
        if city_lower in query or query in city_lower:
            return city, coords[0], coords[1]

    name_clean = name.strip().title()
    hash_val = abs(hash(name)) % 1000
    lat = 20.0 + (hash_val % 100) / 100
    lng = 75.0 + (hash_val // 100) / 10
    return name_clean, lat, lng



def generate_waypoints(src_lat, src_lng, dst_lat, dst_lng, variant_idx):
    points = [(src_lat, src_lng)]
    num_mid = 2 + variant_idx
    for i in range(1, num_mid + 1):
        t = i / (num_mid + 1)
        lat = src_lat + (dst_lat - src_lat) * t + random.uniform(-0.05, 0.05) * variant_idx
        lng = src_lng + (dst_lng - src_lng) * t + random.uniform(-0.05, 0.05) * variant_idx
        points.append((round(lat, 6), round(lng, 6)))
    points.append((dst_lat, dst_lng))
    return points


def travel_difficulty(congestion, risk, distance):
    score = CONGESTION_SCORE.get(congestion, 2) + RISK_SCORE.get(risk, 2)
    if distance > 500:
        score += 1
    if score <= 3:
        return 'Easy'
    if score <= 5:
        return 'Moderate'
    return 'Difficult'


class RouteEngine:
    def __init__(self):
        self.predictor = TrafficPredictor()

    def recommend(self, source, destination, context=None):
        context = context or {}
        
        # 1. Fast check caches sequentially in main thread (thread-safe, no database sharing issues)
        src_cached = resolve_location_cached(source)
        dst_cached = resolve_location_cached(destination)
        
        if src_cached and dst_cached:
            src_name, src_lat, src_lng = src_cached
            dst_name, dst_lat, dst_lng = dst_cached
        else:
            # 2. Parallel API geocoding if uncached (does not access the db inside background threads to prevent concurrency errors)
            from concurrent.futures import ThreadPoolExecutor
            
            def run_geocode(name, cached_val):
                if cached_val:
                    return cached_val
                return geocode_api_call(name)
                
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_src = executor.submit(run_geocode, source, src_cached)
                future_dst = executor.submit(run_geocode, destination, dst_cached)
                src_res = future_src.result()
                dst_res = future_dst.result()
                
            # 3. Handle results and save to Geocode_Cache in main thread
            if src_res:
                src_name, src_lat, src_lng = src_res
                if not src_cached:
                    key = source.strip().lower()
                    _GEOCODE_CACHE[key] = src_res
                    try:
                        from flask import current_app
                        if current_app:
                            from backend.extensions import mysql
                            cur = mysql.connection.cursor()
                            cur.execute(
                                'INSERT INTO Geocode_Cache (query_text, resolved_name, lat, lng) VALUES (%s, %s, %s, %s) '
                                'ON DUPLICATE KEY UPDATE resolved_name = VALUES(resolved_name), lat = VALUES(lat), lng = VALUES(lng)',
                                (key, src_name, src_lat, src_lng)
                            )
                            mysql.connection.commit()
                            cur.close()
                    except Exception:
                        pass
            else:
                src_name, src_lat, src_lng = resolve_location(source)
                
            if dst_res:
                dst_name, dst_lat, dst_lng = dst_res
                if not dst_cached:
                    key = destination.strip().lower()
                    _GEOCODE_CACHE[key] = dst_res
                    try:
                        from flask import current_app
                        if current_app:
                            from backend.extensions import mysql
                            cur = mysql.connection.cursor()
                            cur.execute(
                                'INSERT INTO Geocode_Cache (query_text, resolved_name, lat, lng) VALUES (%s, %s, %s, %s) '
                                'ON DUPLICATE KEY UPDATE resolved_name = VALUES(resolved_name), lat = VALUES(lat), lng = VALUES(lng)',
                                (key, dst_name, dst_lat, dst_lng)
                            )
                            mysql.connection.commit()
                            cur.close()
                    except Exception:
                        pass
            else:
                dst_name, dst_lat, dst_lng = resolve_location(destination)

        osrm_routes = fetch_driving_routes(src_lat, src_lng, dst_lat, dst_lng, count=3)
        if not osrm_routes:
            osrm_routes = [{
                'waypoints': generate_waypoints(src_lat, src_lng, dst_lat, dst_lng, 0),
                'directions': [
                    {'instruction': f'Head towards {dst_name}', 'distance_km': 0, 'duration_min': 0, 'road': ''},
                    {'instruction': 'Arrive at destination', 'distance_km': 0, 'duration_min': 0, 'road': ''},
                ],
                'distance_km': round(haversine(src_lat, src_lng, dst_lat, dst_lng), 2),
                'duration_min': 30,
                'summary': '',
            }]

        routes = []
        for idx, variant in enumerate(ROUTE_VARIANTS):
            osrm = osrm_routes[idx] if idx < len(osrm_routes) else osrm_routes[-1]
            distance = osrm['distance_km']
            base_time = osrm['duration_min']
            congestion_factor = {'Low': 1.0, 'Medium': 1.2, 'High': 1.5}

            pred_input = {
                'city': src_name if src_name in CITY_COORDS else 'Mumbai',
                'weather_condition': context.get('weather_condition', 'Clear'),
                'temperature': context.get('temperature', 28),
                'visibility': context.get('visibility', 8),
                'festival_indicator': context.get('festival_indicator', 0),
                'peak_hour_indicator': context.get('peak_hour_indicator', 1),
                'road_type': variant['road_type'],
                'num_lanes': variant['lanes'],
                'traffic_density': min(100, 40 + idx * 15 + random.uniform(-5, 10)),
            }
            prediction = self.predictor.predict(pred_input)
            congestion = prediction['predicted_congestion']
            est_time = max(1, int(base_time * congestion_factor.get(congestion, 1.2)))
            risk = prediction['traffic_risk']
            difficulty = travel_difficulty(congestion, risk, distance)
            risk_numeric = round(
                CONGESTION_SCORE.get(congestion, 2) * 0.4 +
                RISK_SCORE.get(risk, 2) * 0.4 +
                (distance / 1000) * 0.2, 2
            )

            label = variant['label']
            if osrm.get('summary'):
                label = osrm['summary'] if idx == 0 else variant['label']

            routes.append({
                'route_name': variant['name'],
                'route_label': label,
                'distance_km': distance,
                'estimated_time_min': est_time,
                'predicted_congestion': congestion,
                'confidence_score': prediction['confidence_score'],
                'risk_score': risk_numeric,
                'traffic_risk': risk,
                'travel_difficulty': difficulty,
                'road_type': variant['road_type'],
                'waypoints': osrm['waypoints'],
                'directions': osrm['directions'],
                'source': {'name': src_name, 'lat': src_lat, 'lng': src_lng},
                'destination': {'name': dst_name, 'lat': dst_lat, 'lng': dst_lng},
            })

        routes.sort(key=lambda r: (
            CONGESTION_SCORE.get(r['predicted_congestion'], 2),
            r['risk_score'],
            r['estimated_time_min']
        ))
        preference = context.get('route_preference', 'fastest')
        best = self._pick_best_route(routes, preference)
        explanation = self._build_explanation(best, preference)

        suggestions = self._generate_suggestions(routes, context)
        return {
            'source': source,
            'destination': destination,
            'routes': routes,
            'recommended_route': best['route_name'],
            'explanation': explanation,
            'suggestions': suggestions,
        }

    def _generate_suggestions(self, routes, context):
        suggestions = []
        peak = int(context.get('peak_hour_indicator', 0))
        festival = int(context.get('festival_indicator', 0))
        high_congestion = any(r['predicted_congestion'] == 'High' for r in routes)

        if peak or high_congestion:
            suggestions.append('Leave 15 minutes earlier to avoid peak-hour delays.')
        if peak:
            suggestions.append('Avoid peak-hour travel between 7-10 AM and 5-8 PM if possible.')
        if festival:
            suggestions.append('Festival period detected — expect higher traffic near event areas.')
        if context.get('weather_condition') in ('Rain', 'Storm'):
            suggestions.append('Rainy conditions detected — drive cautiously and allow extra time.')
        if any(r['travel_difficulty'] == 'Difficult' for r in routes):
            suggestions.append('Consider alternate routes with lower congestion levels.')
        if not suggestions:
            suggestions.append('Traffic conditions look favorable — safe travels!')
        return suggestions

    def _pick_best_route(self, routes, preference):
        if preference == 'fuel':
            return min(routes, key=lambda r: (r['distance_km'], r['estimated_time_min']))
        if preference == 'avoid_tolls':
            non_highway = [r for r in routes if r.get('road_type') != 'Highway']
            pool = non_highway or routes
            return min(pool, key=lambda r: (r['estimated_time_min'], r['risk_score']))
        return routes[0]

    def _build_explanation(self, best, preference):
        pref_text = {
            'fastest': 'fastest travel time',
            'fuel': 'shorter distance to save fuel',
            'avoid_tolls': 'avoiding toll roads when possible',
        }.get(preference, 'lowest congestion and risk')
        return (
            f"{best['route_name']} is recommended based on your preference for {pref_text}. "
            f"Predicted congestion: {best['predicted_congestion']}, "
            f"risk: {best['traffic_risk']}, estimated time: {best['estimated_time_min']} minutes."
        )

    def get_heatmap_data(self):
        data = []
        predictor = TrafficPredictor()
        for city, (lat, lng) in CITY_COORDS.items():
            for hour in [8, 12, 18]:
                pred = predictor.predict({
                    'city': city,
                    'weather_condition': 'Clear',
                    'temperature': 30,
                    'visibility': 8,
                    'peak_hour_indicator': 1 if hour in (8, 18) else 0,
                    'festival_indicator': 0,
                    'road_type': 'Urban',
                    'num_lanes': 3,
                    'traffic_density': 55,
                    'hour': hour,
                })
                intensity = CONGESTION_SCORE.get(pred['predicted_congestion'], 2)
                data.append({
                    'city': city,
                    'lat': lat,
                    'lng': lng,
                    'hour': hour,
                    'congestion': pred['predicted_congestion'],
                    'intensity': intensity,
                })
        return data
