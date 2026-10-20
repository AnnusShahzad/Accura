#!/usr/bin/env bash
# Start the API and the web server side by side. If either stops, stop the
# container too, so the platform restarts it rather than serving half an app.
set -uo pipefail

PORT="${PORT:-10000}"

# The API is internal only. APP_PORT beats a platform-provided PORT, which
# belongs to the web server.
(cd /app/backend && exec env APP_HOST=127.0.0.1 APP_PORT=8000 python app.py) &
api=$!

(cd /app/web && exec env HOSTNAME=0.0.0.0 PORT="$PORT" node frontend/server.js) &
web=$!

stopping=0
trap 'stopping=1; kill -TERM "$api" "$web" 2>/dev/null' TERM INT

wait -n "$api" "$web"
status=$?
if [ "$stopping" -eq 1 ]; then
  wait
  exit 0
fi
# Neither process should ever stop on its own. Report failure even if it
# exited "cleanly", so the platform restarts the container.
echo "start-accura: a process exited unexpectedly (status $status); stopping" >&2
kill -TERM "$api" "$web" 2>/dev/null
wait
exit $(( status == 0 ? 1 : status ))
