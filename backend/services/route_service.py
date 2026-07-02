from backend.extensions import mysql


def save_travel_history(user_id, route_data, recommended):
    cur = mysql.connection.cursor()
    best = next((r for r in route_data['routes'] if r['route_name'] == recommended), route_data['routes'][0])
    cur.execute('''
        INSERT INTO Travel_History
        (user_id, source_location, destination_location, route_name,
         predicted_congestion, risk_score, travel_difficulty,
         distance_km, estimated_time_min, weather_condition)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        user_id, route_data['source'], route_data['destination'],
        best['route_name'], best['predicted_congestion'],
        best['risk_score'], best['travel_difficulty'],
        best['distance_km'], best['estimated_time_min'],
        route_data.get('weather_condition', 'Clear')
    ))
    mysql.connection.commit()
    history_id = cur.lastrowid
    cur.close()
    return history_id


def get_travel_history(user_id, limit=50):
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT history_id, source_location, destination_location, route_name,
               predicted_congestion, risk_score, travel_difficulty,
               distance_km, estimated_time_min, weather_condition, travel_date
        FROM Travel_History WHERE user_id = %s
        ORDER BY travel_date DESC LIMIT %s
    ''', (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def delete_travel_history_item(user_id, history_id):
    cur = mysql.connection.cursor()
    cur.execute(
        'DELETE FROM Travel_History WHERE history_id = %s AND user_id = %s',
        (history_id, user_id),
    )
    mysql.connection.commit()
    deleted = cur.rowcount
    cur.close()
    return deleted > 0


def clear_travel_history(user_id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM Travel_History WHERE user_id = %s', (user_id,))
    mysql.connection.commit()
    deleted = cur.rowcount
    cur.close()
    return deleted


def save_route(user_id, data):
    cur = mysql.connection.cursor()
    cur.execute('''
        INSERT INTO Saved_Routes
        (user_id, route_name, source_location, destination_location,
         preferred_route, source_lat, source_lng, dest_lat, dest_lng)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        user_id, data['route_name'], data['source'], data['destination'],
        data.get('preferred_route', 'Route A'),
        data.get('source_lat'), data.get('source_lng'),
        data.get('dest_lat'), data.get('dest_lng')
    ))
    mysql.connection.commit()
    route_id = cur.lastrowid
    cur.close()
    return route_id


def get_saved_routes(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT route_id, route_name, source_location, destination_location,
               preferred_route, use_count, created_at, last_used
        FROM Saved_Routes WHERE user_id = %s ORDER BY created_at DESC
    ''', (user_id,))
    rows = cur.fetchall()
    cur.close()
    return rows


def delete_saved_route(user_id, route_id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM Saved_Routes WHERE route_id = %s AND user_id = %s', (route_id, user_id))
    mysql.connection.commit()
    deleted = cur.rowcount
    cur.close()
    return deleted > 0
