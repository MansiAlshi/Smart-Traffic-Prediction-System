from backend.extensions import mysql
from backend.ml.predictor import TrafficPredictor


def save_prediction(user_id, data, result):
    cur = mysql.connection.cursor()
    cur.execute('''
        INSERT INTO Predictions
        (user_id, city, source_location, destination_location, travel_date, travel_time,
         weather_condition, temperature, visibility,
         festival_indicator, peak_hour_indicator, road_type, num_lanes,
         traffic_density, predicted_congestion, confidence_score, traffic_risk)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        user_id, data['city'], data.get('source', ''), data.get('destination', ''),
        data.get('travel_date', ''), data.get('travel_time', ''),
        data['weather_condition'],
        data.get('temperature', 28), data.get('visibility', 8),
        int(data.get('festival_indicator', 0)), int(data.get('peak_hour_indicator', 0)),
        data['road_type'], int(data.get('num_lanes', 2)),
        float(data.get('traffic_density', 50)),
        result['predicted_congestion'], result['confidence_score'],
        result['traffic_risk']
    ))
    mysql.connection.commit()
    pred_id = cur.lastrowid
    cur.close()
    return pred_id


def get_user_predictions(user_id, limit=10):
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT prediction_id, city, weather_condition, predicted_congestion,
               confidence_score, traffic_risk, created_at
        FROM Predictions WHERE user_id = %s
        ORDER BY created_at DESC LIMIT %s
    ''', (user_id, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_prediction_count(user_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT COUNT(*) as cnt FROM Predictions WHERE user_id = %s', (user_id,))
    row = cur.fetchone()
    cur.close()
    return row['cnt'] if row else 0
