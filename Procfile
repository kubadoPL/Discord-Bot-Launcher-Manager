worker: python launcher.py
web: gunicorn -k gevent -w 1 --bind 0.0.0.0:$PORT webAppsLauncher:application