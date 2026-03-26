#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${RESUME_APP_HOST:-127.0.0.1}"
PORT="${RESUME_APP_PORT:-8080}"
PID_FILE="${RESUME_APP_PID_FILE:-/tmp/recruitment-system-resume-app.pid}"
LOG_FILE="${RESUME_APP_LOG_FILE:-/tmp/recruitment-system-resume-app.log}"

is_running() {
  local pid="$1"
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi
  local cmdline
  cmdline="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$cmdline" == *"app/server.py"* ]]
}

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && is_running "$old_pid"; then
    echo "resume app already running: pid=$old_pid host=$HOST port=$PORT"
    echo "log: $LOG_FILE"
    exit 0
  fi
fi

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"
: >"$LOG_FILE"

nohup env PYTHONUNBUFFERED=1 RESUME_APP_HOST="$HOST" RESUME_APP_PORT="$PORT" \
  python3 app/server.py >>"$LOG_FILE" 2>&1 &
new_pid="$!"
echo "$new_pid" >"$PID_FILE"

sleep 1
if is_running "$new_pid"; then
  echo "resume app started: pid=$new_pid host=$HOST port=$PORT"
  echo "pid file: $PID_FILE"
  echo "log: $LOG_FILE"
  exit 0
fi

echo "failed to start resume app, last log lines:"
tail -n 40 "$LOG_FILE" || true
exit 1
