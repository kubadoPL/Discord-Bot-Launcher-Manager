#!/usr/bin/env bash
# Web dyno entrypoint.
#
# Two processes on the dyno:
#   1. the streaming engine (StreamerApi only) on 127.0.0.1:$STREAMER_PORT
#   2. the web app (chat, downloader, K5, ...) on 0.0.0.0:$PORT, which proxies
#      /StreamerApi/* to the engine and pulls /public/status from it.
# The Icecast feed loop therefore never shares a GIL with the HTTP handlers.
#
# STREAMER_SEPARATE=0 restores the old single-process layout.
set -u
cd "$(dirname "$0")"

COMMON="-c gunicorn.conf.py -k gthread -w 1 --graceful-timeout 8 --keep-alive 5"

if [ "${STREAMER_SEPARATE:-1}" != "1" ]; then
  exec gunicorn $COMMON --threads 24 --timeout 120 --bind "0.0.0.0:${PORT}" webAppsLauncher:application
fi

STREAMER_PORT="${STREAMER_PORT:-5055}"
export STREAMER_UPSTREAM="http://127.0.0.1:${STREAMER_PORT}"

# Engine: few threads, long timeout (downloads), one DB connection of the shared quota.
STREAMER_STANDALONE=1 DB_POOL_SIZE="${STREAMER_DB_POOL_SIZE:-1}" \
  gunicorn $COMMON --threads 8 --timeout 300 --bind "127.0.0.1:${STREAMER_PORT}" streamerLauncher:application &
ENGINE_PID=$!

gunicorn $COMMON --threads 24 --timeout 120 --bind "0.0.0.0:${PORT}" webAppsLauncher:application &
WEB_PID=$!

term() { kill -TERM "$WEB_PID" "$ENGINE_PID" 2>/dev/null; }
trap term TERM INT

# If either process dies the dyno exits and Heroku restarts both together.
wait -n "$WEB_PID" "$ENGINE_PID"
term
wait
