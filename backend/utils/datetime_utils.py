from datetime import datetime


def format_datetime(value):
    """Format SQLite string or datetime for API/JSON responses."""
    if not value:
        return None
    if isinstance(value, str):
        return value[:19] if len(value) >= 19 else value
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return str(value)
