#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
API_PID_FILE="$ROOT_DIR/.guestbook-api.pid"

run_api() {
  echo "[API] Setup and start FastAPI..."
  cd "$BACKEND_DIR"

  if [ ! -d ".venv" ]; then
    python -m venv .venv
  fi

  # shellcheck disable=SC1091
  source ".venv/bin/activate"
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000
}

run_front() {
  echo "[FRONT] Install and start React..."
  cd "$FRONTEND_DIR"
  npm install
  npm run dev
}

stop_api() {
  echo "[STOP] Stopping API..."

  if [ -f "$API_PID_FILE" ]; then
    API_PID="$(cat "$API_PID_FILE")"
    if kill -0 "$API_PID" 2>/dev/null; then
      kill "$API_PID" 2>/dev/null || true
      echo "[STOP] Stopped API PID $API_PID."
    else
      echo "[STOP] PID file found but process is not running."
    fi
    rm -f "$API_PID_FILE"
  else
    echo "[STOP] No PID file found."
  fi

  if command -v pkill >/dev/null 2>&1; then
    pkill -f "uvicorn app.main:app --reload --port 8000" >/dev/null 2>&1 || true
  fi
}

case "$MODE" in
  api)
    run_api
    ;;
  front)
    run_front
    ;;
  all)
    echo "[ALL] Starting API in background and Front in foreground..."
    stop_api
    (
      cd "$BACKEND_DIR"
      if [ ! -d ".venv" ]; then
        python -m venv .venv
      fi
      # shellcheck disable=SC1091
      source ".venv/bin/activate"
      pip install -r requirements.txt
      nohup uvicorn app.main:app --reload --port 8000 > /tmp/guestbook-api.log 2>&1 &
      echo $! > "$API_PID_FILE"
      echo "[ALL] API PID saved to $API_PID_FILE"
    )
    run_front
    ;;
  stop)
    stop_api
    ;;
  *)
    echo "Usage: $0 [api|front|all|stop]"
    exit 1
    ;;
esac
