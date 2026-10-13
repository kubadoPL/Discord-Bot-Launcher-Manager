"""gunicorn server hooks (loaded via `-c gunicorn.conf.py` in the Procfile).

The only job here is to make sure the MySQL connection pool is closed
cleanly whenever a worker or the master process goes away, so a dyno
restart does not leave idle sessions open on the database server.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _close_pool(where):
    mod = sys.modules.get("api.FunctionsModule")
    if mod is None:
        return  # pool was never created in this process
    try:
        mod.close_db_pool()
    except Exception as e:  # never block shutdown
        print(f"[gunicorn:{where}] close_db_pool failed: {e}")


def worker_exit(server, worker):
    _close_pool("worker_exit")


def on_exit(server):
    _close_pool("on_exit")
