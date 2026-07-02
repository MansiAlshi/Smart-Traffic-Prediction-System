from backend.ml.route_engine import RouteEngine


def get_heatmap_data():
    engine = RouteEngine()
    return engine.get_heatmap_data()
