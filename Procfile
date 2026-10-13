worker: python launcher.py
web: gunicorn -c gunicorn.conf.py -k gthread -w 1 --threads 24 --timeout 120 --keep-alive 5 --bind 0.0.0.0:$PORT webAppsLauncher:application
