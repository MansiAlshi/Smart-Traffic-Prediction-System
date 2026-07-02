"""
Data generation script mimicking Indian Road Accident Dataset (2022-2025) structure.
Place the actual Kaggle CSV at ml/data/traffic_dataset.csv to use real data.
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

CITIES = [
    'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai',
    'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow',
    'Chandigarh', 'Kochi', 'Indore', 'Bhopal', 'Nagpur'
]

WEATHER = ['Clear', 'Cloudy', 'Rain', 'Fog', 'Storm', 'Haze']
ROAD_TYPES = ['Highway', 'Urban', 'Rural', 'Expressway', 'Suburban']
LIGHT = ['Daylight', 'Dark - lit', 'Dark - unlit', 'Dusk/Dawn']
SURFACE = ['Dry', 'Wet', 'Icy', 'Muddy']

FESTIVAL_DATES = [
    (1, 26), (3, 8), (3, 25), (4, 14), (8, 15),
    (10, 2), (10, 24), (11, 12), (12, 25)
]

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
}


def is_festival(month, day):
    return (month, day) in FESTIVAL_DATES


def is_peak_hour(hour):
    return 1 if (7 <= hour <= 10) or (17 <= hour <= 20) else 0


def weather_severity(weather):
    mapping = {'Clear': 0.1, 'Cloudy': 0.3, 'Haze': 0.4, 'Fog': 0.6, 'Rain': 0.7, 'Storm': 0.9}
    return mapping.get(weather, 0.3)


def compute_congestion(row):
    score = 0.0
    score += row['peak_hour_indicator'] * 0.35
    score += row['weather_severity'] * 0.2
    score += row['festival_impact'] * 0.15
    score += (row['traffic_density'] / 100) * 0.25
    if row['road_type'] == 'Urban':
        score += 0.15
    elif row['road_type'] == 'Highway':
        score += 0.05
    if row['num_lanes'] <= 2:
        score += 0.1
    if row['visibility'] < 2:
        score += 0.1
    if row['is_weekend']:
        score += 0.08
    noise = np.random.normal(0, 0.05)
    score = max(0, min(1, score + noise))
    if score < 0.35:
        return 'Low'
    if score < 0.65:
        return 'Medium'
    return 'High'


def generate_dataset(n_records=15000, seed=42):
    np.random.seed(seed)
    start_date = datetime(2022, 1, 1)
    records = []

    for i in range(n_records):
        city = np.random.choice(CITIES)
        lat, lng = CITY_COORDS[city]
        lat += np.random.uniform(-0.15, 0.15)
        lng += np.random.uniform(-0.15, 0.15)

        days_offset = np.random.randint(0, 1400)
        dt = start_date + timedelta(days=int(days_offset))
        hour_probs = [0.02, 0.01, 0.01, 0.01, 0.02, 0.03, 0.04, 0.06, 0.07, 0.06,
                      0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.06, 0.07, 0.08, 0.07,
                      0.05, 0.04, 0.03, 0.02]
        hour_probs = np.array(hour_probs) / np.sum(hour_probs)
        hour = int(np.random.choice(list(range(24)), p=hour_probs))

        weather = np.random.choice(WEATHER, p=[0.35, 0.25, 0.15, 0.08, 0.07, 0.10])
        road_type = np.random.choice(ROAD_TYPES, p=[0.25, 0.35, 0.15, 0.15, 0.10])
        num_lanes = int(np.random.choice([1, 2, 3, 4, 6], p=[0.1, 0.3, 0.35, 0.2, 0.05]))
        festival = 1 if is_festival(dt.month, dt.day) else 0
        peak = is_peak_hour(hour)
        is_weekend = 1 if dt.weekday() >= 5 else 0

        base_temp = 28 + np.random.normal(0, 5)
        if weather == 'Rain':
            base_temp -= 5
        if weather == 'Storm':
            base_temp -= 8

        visibility = max(0.5, min(10, np.random.normal(8, 2)))
        if weather in ('Fog', 'Rain', 'Storm'):
            visibility = max(0.5, visibility - np.random.uniform(2, 5))

        density = np.random.beta(2, 2) * 100
        if peak:
            density = min(100, density + np.random.uniform(15, 35))
        if festival:
            density = min(100, density + np.random.uniform(10, 25))

        ws = weather_severity(weather)
        festival_impact = 0.8 if festival else 0.0

        row = {
            'accident_id': f'ACC{i+1:06d}',
            'city': city,
            'state': city,
            'date': dt.strftime('%Y-%m-%d'),
            'time': f'{hour:02d}:{np.random.randint(0,60):02d}',
            'hour': hour,
            'day': dt.day,
            'month': dt.month,
            'year': dt.year,
            'day_of_week': dt.weekday(),
            'is_weekend': is_weekend,
            'peak_hour_indicator': peak,
            'festival_indicator': festival,
            'festival_impact': festival_impact,
            'weather_condition': weather,
            'weather_severity': ws,
            'temperature': round(base_temp, 1),
            'visibility': round(visibility, 2),
            'road_type': road_type,
            'num_lanes': num_lanes,
            'light_conditions': np.random.choice(LIGHT),
            'road_surface': np.random.choice(SURFACE),
            'traffic_density': round(density, 2),
            'latitude': round(lat, 6),
            'longitude': round(lng, 6),
            'urban_or_rural': 'Urban' if road_type in ('Urban', 'Suburban') else 'Rural',
            'speed_limit': int(np.random.choice([40, 50, 60, 80, 100])),
        }
        row['congestion_level'] = compute_congestion(row)
        records.append(row)

    return pd.DataFrame(records)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'traffic_dataset.csv')

    if os.path.exists(out_path):
        print(f'Dataset already exists at {out_path}')
        return out_path

    df = generate_dataset()
    df.to_csv(out_path, index=False)
    print(f'Generated {len(df)} records -> {out_path}')
    print(df['congestion_level'].value_counts())
    return out_path


if __name__ == '__main__':
    main()
