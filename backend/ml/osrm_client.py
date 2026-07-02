import json
import math
import urllib.parse
import urllib.request

OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving'

MANEUVER_TEXT = {
    'depart': 'Start on {road}',
    'arrive': 'Arrive at destination',
    'turn': 'Turn {modifier} onto {road}',
    'new name': 'Continue onto {road}',
    'merge': 'Merge {modifier} onto {road}',
    'on ramp': 'Take the ramp {modifier} onto {road}',
    'off ramp': 'Take the exit {modifier} onto {road}',
    'fork': 'Keep {modifier} at the fork onto {road}',
    'end of road': 'At the end of the road, turn {modifier} onto {road}',
    'continue': 'Continue on {road}',
    'roundabout': 'Take the roundabout onto {road}',
    'rotary': 'Enter the rotary onto {road}',
    'roundabout turn': 'Take the roundabout exit onto {road}',
}


def _request_osrm(coords_list, alternatives=False):
    """coords_list: [(lng, lat), ...]"""
    coord_str = ';'.join(f'{lng},{lat}' for lng, lat in coords_list)
    params = urllib.parse.urlencode({
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'true',
        'alternatives': 'true' if alternatives else 'false',
    })
    url = f'{OSRM_BASE}/{coord_str}?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': 'SmartTrafficAI/1.0'})
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode())
    if data.get('code') != 'Ok' or not data.get('routes'):
        raise ValueError(data.get('message', 'Routing failed'))
    return data['routes']


def _format_modifier(modifier):
    mapping = {
        'straight': 'straight',
        'slight right': 'slight right',
        'right': 'right',
        'sharp right': 'sharp right',
        'slight left': 'slight left',
        'left': 'left',
        'sharp left': 'sharp left',
        'uturn': 'around',
    }
    return mapping.get(modifier, modifier or '')


def _bearing_to_cardinal(bearing):
    if bearing is None:
        return None
    try:
        b = float(bearing) % 360
    except (TypeError, ValueError):
        return None
    dirs = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']
    idx = int((b + 22.5) // 45) % 8
    return dirs[idx]


def _ordinal(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if 10 <= (n % 100) <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def _format_step(step):
    maneuver = step.get('maneuver', {})
    mtype = maneuver.get('type', 'continue')
    modifier = _format_modifier(maneuver.get('modifier', ''))
    road = (step.get('name') or '').strip()
    road_label = road or 'the road'
    exit_no = maneuver.get('exit')
    bearing_after = maneuver.get('bearing_after')
    cardinal = _bearing_to_cardinal(bearing_after)
    loc = maneuver.get('location')
    step_latlng = None
    if isinstance(loc, (list, tuple)) and len(loc) == 2:
        # OSRM provides [lon, lat]
        step_latlng = [loc[1], loc[0]]

    if mtype == 'depart':
        if road:
            instruction = f'Head {cardinal} on {road}' if cardinal else f'Head on {road}'
        else:
            instruction = f'Head {cardinal}' if cardinal else 'Start'
    elif mtype == 'arrive':
        instruction = 'Arrive at destination'
    elif mtype in ('roundabout', 'rotary', 'roundabout turn'):
        ord_exit = _ordinal(exit_no)
        if ord_exit and road:
            instruction = f'At the roundabout, take the {ord_exit} exit onto {road}'
        elif ord_exit:
            instruction = f'At the roundabout, take the {ord_exit} exit'
        else:
            instruction = f'Continue through the roundabout onto {road_label}'
    else:
        template = MANEUVER_TEXT.get(mtype, 'Continue on {road}')
        if mtype == 'continue' and cardinal and not road:
            instruction = f'Head {cardinal}'
        elif '{modifier}' in template:
            instruction = template.format(modifier=modifier, road=road_label)
        else:
            instruction = template.format(road=road_label)

    return {
        'instruction': instruction,
        'distance_km': round(step.get('distance', 0) / 1000, 2),
        'duration_min': max(1, int(round(step.get('duration', 0) / 60))),
        'road': road_label,
        'latlng': step_latlng,
        'maneuver': {
            'type': mtype,
            'modifier': modifier or None,
            'exit': exit_no,
            'bearing_after': bearing_after,
        },
    }


def _parse_route(route):
    geometry = route.get('geometry', {})
    coords = geometry.get('coordinates', [])
    waypoints = [[lat, lng] for lng, lat in coords]

    directions = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            directions.append(_format_step(step))

    distance_km = round(route.get('distance', 0) / 1000, 2)
    duration_min = max(1, int(round(route.get('duration', 0) / 60)))

    road_names = [s['road'] for s in directions if s['road'] and s['road'] != 'the road'][:3]
    summary = 'via ' + ', '.join(road_names) if road_names else ''

    return {
        'waypoints': waypoints,
        'directions': directions,
        'distance_km': distance_km,
        'duration_min': duration_min,
        'summary': summary,
    }


def _via_point(src_lat, src_lng, dst_lat, dst_lng, offset_factor):
    mid_lat = (src_lat + dst_lat) / 2
    mid_lng = (src_lng + dst_lng) / 2
    dlat = dst_lat - src_lat
    dlng = dst_lng - src_lng
    length = math.sqrt(dlat ** 2 + dlng ** 2) or 1
    perp_lat = -dlng / length * offset_factor
    perp_lng = dlat / length * offset_factor
    return mid_lng + perp_lng, mid_lat + perp_lat


def _fetch_alt_route(src_lat, src_lng, dst_lat, dst_lng, offset):
    try:
        via_lng, via_lat = _via_point(src_lat, src_lng, dst_lat, dst_lng, offset)
        alt = _request_osrm(
            [(src_lng, src_lat), (via_lng, via_lat), (dst_lng, dst_lat)],
            alternatives=False,
        )
        parsed_routes = []
        for r in alt:
            parsed = _parse_route(r)
            if parsed['waypoints']:
                parsed_routes.append(parsed)
        return parsed_routes
    except Exception:
        return []


def fetch_driving_routes(src_lat, src_lng, dst_lat, dst_lng, count=3):
    """Return up to `count` distinct driving routes with directions."""
    # 1. DB Cache Check
    route_key = f"{src_lat:.4f},{src_lng:.4f}->{dst_lat:.4f},{dst_lng:.4f}"
    try:
        from flask import current_app
        if current_app:
            from backend.extensions import mysql
            cur = mysql.connection.cursor()
            cur.execute('SELECT route_data FROM Route_Cache WHERE route_key = %s', (route_key,))
            row = cur.fetchone()
            cur.close()
            if row:
                cached_routes = json.loads(row['route_data'])
                if cached_routes:
                    return cached_routes
    except Exception:
        pass

    routes = []
    seen = set()

    def add_unique(parsed):
        key = round(parsed['distance_km'], 1)
        if key in seen and len(routes) > 0:
            return False
        seen.add(key)
        routes.append(parsed)
        return True

    try:
        primary = _request_osrm([(src_lng, src_lat), (dst_lng, dst_lat)], alternatives=True)
        for r in primary:
            parsed = _parse_route(r)
            if parsed['waypoints']:
                add_unique(parsed)
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    # If we need more routes, fetch alternatives in parallel
    if len(routes) < count:
        offsets = [0.08, -0.08, 0.15, -0.15]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(offsets)) as executor:
            futures = [
                executor.submit(_fetch_alt_route, src_lat, src_lng, dst_lat, dst_lng, offset)
                for offset in offsets
            ]
            for future in futures:
                alt_routes = future.result()
                for parsed in alt_routes:
                    if len(routes) >= count:
                        break
                    add_unique(parsed)
                if len(routes) >= count:
                    break

    final_routes = routes[:count]

    # Save to database cache
    if final_routes:
        try:
            from flask import current_app
            if current_app:
                from backend.extensions import mysql
                cur = mysql.connection.cursor()
                cur.execute(
                    'INSERT INTO Route_Cache (route_key, route_data) VALUES (%s, %s) '
                    'ON DUPLICATE KEY UPDATE route_data = VALUES(route_data)',
                    (route_key, json.dumps(final_routes))
                )
                mysql.connection.commit()
                cur.close()
        except Exception:
            pass

    return final_routes

