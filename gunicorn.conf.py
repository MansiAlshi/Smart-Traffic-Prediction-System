import os

# Render sets PORT env var; default to 10000 for local gunicorn testing
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# 2 workers per CPU core is typical for I/O-bound Flask apps
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = "sync"

# Timeouts (ML model loading can take a few seconds)
timeout = 120
keepalive = 5

# Logging
accesslog = "-"   # stdout
errorlog  = "-"   # stderr
loglevel  = "info"
