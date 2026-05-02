#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

API_HOST="${GUMROAD_MERCHANT_API_HOST:-127.0.0.1}"
API_PORT="${GUMROAD_MERCHANT_API_PORT:-8001}"
UI_HOST="${GUMROAD_MERCHANT_UI_HOST:-127.0.0.1}"
UI_PORT="${GUMROAD_MERCHANT_UI_PORT:-8080}"
API_URL="http://${API_HOST}:${API_PORT}"
UI_URL="http://${UI_HOST}:${UI_PORT}"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BOOTSTRAP="${PYTHON:-python3}"
PYTHON_BIN="$VENV_DIR/bin/python"
LOG_DIR="$PROJECT_ROOT/artifacts/run_logs"

INSTALL_DEPS=1
RUN_MCP_SMOKE=1
ONCE=0
MCP_STDIO=0
API_PID=""
UI_PID=""

log() {
  printf '[gumroad-merchant] %s\n' "$*" >&2
}

die() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage: scripts/start-gumroad-merchant.sh [options]

Installs dependencies, starts the Gumroad Merchant API, starts the browser demo,
and verifies the MCP stdio server.

Options:
  --once           Start/reuse services, run checks, then exit.
  --skip-install   Do not install Python/npm dependencies.
  --no-mcp-smoke   Skip the MCP smoke verification.
  --mcp-stdio      Start/reuse API/UI, then run the MCP stdio server in foreground.
  -h, --help       Show this help.

Default URLs:
  Browser UI: http://127.0.0.1:8080/
  API:        http://127.0.0.1:8001/api/health
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --once)
      ONCE=1
      ;;
    --skip-install)
      INSTALL_DEPS=0
      ;;
    --no-mcp-smoke)
      RUN_MCP_SMOKE=0
      ;;
    --mcp-stdio)
      MCP_STDIO=1
      RUN_MCP_SMOKE=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      die "Unknown option: $1"
      ;;
  esac
  shift
done

cleanup() {
  local status=$?
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    log "Stopping backend API (pid $API_PID)."
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$UI_PID" ]] && kill -0 "$UI_PID" >/dev/null 2>&1; then
    log "Stopping browser demo (pid $UI_PID)."
    kill "$UI_PID" >/dev/null 2>&1 || true
  fi
  wait "$API_PID" "$UI_PID" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT"
mkdir -p "$LOG_DIR"

ensure_python() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    log "Creating Python virtualenv at .venv."
    "$PYTHON_BOOTSTRAP" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required for the Gumroad Merchant MCP server.")
PY
    "$PYTHON_BOOTSTRAP" -m venv "$VENV_DIR"
  fi

  "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required for the Gumroad Merchant MCP server.")
PY
}

has_node_dependencies() {
  "$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
package = json.loads(Path("package.json").read_text(encoding="utf-8"))
deps = package.get("dependencies") or {}
dev_deps = package.get("devDependencies") or {}
raise SystemExit(0 if deps or dev_deps else 1)
PY
}

install_dependencies() {
  ensure_python

  if [[ "$INSTALL_DEPS" -eq 0 ]]; then
    log "Skipping dependency install."
    return
  fi

  log "Installing Python dependencies."
  "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
  "$PYTHON_BIN" -m pip install -r requirements.txt

  if command -v npm >/dev/null 2>&1; then
    if [[ -f package-lock.json ]]; then
      log "Installing npm dependencies with npm ci."
      npm ci
    elif has_node_dependencies; then
      log "Installing npm dependencies with npm install."
      npm install
    else
      log "No npm dependencies declared; skipping npm install."
    fi
  else
    log "npm is not installed or not on PATH; skipping npm install because this demo has no declared npm dependencies."
  fi
}

url_ok() {
  local url="$1"
  "$PYTHON_BIN" - "$url" <<'PY' >/dev/null 2>&1
from urllib.request import urlopen
import sys
url = sys.argv[1]
with urlopen(url, timeout=2) as response:
    if response.status >= 400:
        raise SystemExit(1)
PY
}

post_ok() {
  local url="$1"
  "$PYTHON_BIN" - "$url" <<'PY' >/dev/null 2>&1
from urllib.request import Request, urlopen
import sys
request = Request(sys.argv[1], method="POST")
with urlopen(request, timeout=20) as response:
    if response.status >= 400:
        raise SystemExit(1)
PY
}

port_open() {
  local host="$1"
  local port="$2"
  "$PYTHON_BIN" - "$host" "$port" <<'PY' >/dev/null 2>&1
import socket
import sys
host, port = sys.argv[1], int(sys.argv[2])
with socket.create_connection((host, port), timeout=1):
    pass
PY
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"

  for _ in $(seq 1 "$attempts"); do
    if url_ok "$url"; then
      return 0
    fi
    sleep 0.5
  done

  die "$label did not become ready at $url"
}

start_api() {
  local api_log="$LOG_DIR/backend-api.log"

  if url_ok "$API_URL/api/health"; then
    log "Backend API already running at $API_URL; reusing it."
    return
  fi

  if port_open "$API_HOST" "$API_PORT"; then
    die "Port $API_PORT is already in use, but $API_URL/api/health did not respond."
  fi

  log "Starting backend API at $API_URL."
  "$PYTHON_BIN" -m uvicorn backend.api:app --host "$API_HOST" --port "$API_PORT" >"$api_log" 2>&1 &
  API_PID=$!
  wait_for_url "$API_URL/api/health" "Backend API"
}

start_ui() {
  local ui_log="$LOG_DIR/browser-demo.log"

  if url_ok "$UI_URL/index.html"; then
    log "Browser demo already running at $UI_URL; reusing it."
    return
  fi

  if port_open "$UI_HOST" "$UI_PORT"; then
    die "Port $UI_PORT is already in use, but $UI_URL/index.html did not respond."
  fi

  log "Starting browser demo at $UI_URL."
  "$PYTHON_BIN" -m http.server "$UI_PORT" --bind "$UI_HOST" --directory demo >"$ui_log" 2>&1 &
  UI_PID=$!
  wait_for_url "$UI_URL/index.html" "Browser demo"
}

smoke_services() {
  log "Refreshing seeded analytics data."
  post_ok "$API_URL/api/agent/data/refresh?force=true" || die "Data refresh failed."
  wait_for_url "$API_URL/api/analytics/summary?product_id=all&date_range=30" "Analytics summary" 20
}

smoke_mcp() {
  if [[ "$RUN_MCP_SMOKE" -eq 0 ]]; then
    log "Skipping MCP smoke verification."
    return
  fi

  log "Verifying MCP stdio server."
  GUMROAD_MERCHANT_PYTHON="$PYTHON_BIN" GUMROAD_MERCHANT_MODE="${GUMROAD_MERCHANT_MODE:-seeded}" \
    "$PYTHON_BIN" scripts/run_mcp_smoke.py
}

print_ready() {
  cat >&2 <<EOF

Gumroad Merchant is running.

Browser UI:
  $UI_URL/

Backend API:
  $API_URL/api/health

MCP stdio command for Codex/Claude/Cursor:
  $PROJECT_ROOT/scripts/start-gumroad-merchant.sh --mcp-stdio

Logs:
  $LOG_DIR/backend-api.log
  $LOG_DIR/browser-demo.log

Press Ctrl-C to stop services started by this script.
EOF
}

run_mcp_stdio() {
  export GUMROAD_MERCHANT_PYTHON="$PYTHON_BIN"
  export GUMROAD_MERCHANT_MODE="${GUMROAD_MERCHANT_MODE:-seeded}"
  log "Starting Gumroad Merchant MCP stdio server. Protocol output is reserved for the MCP client."
  "$PROJECT_ROOT/scripts/gumroad-merchant-mcp.sh"
}

install_dependencies
start_api
start_ui
smoke_services

if [[ "$MCP_STDIO" -eq 1 ]]; then
  run_mcp_stdio
  exit 0
fi

smoke_mcp
print_ready

if [[ "$ONCE" -eq 1 ]]; then
  log "--once provided; exiting after successful startup verification."
  exit 0
fi

while true; do
  if [[ -n "$API_PID" ]] && ! kill -0 "$API_PID" >/dev/null 2>&1; then
    die "Backend API exited. Check $LOG_DIR/backend-api.log"
  fi
  if [[ -n "$UI_PID" ]] && ! kill -0 "$UI_PID" >/dev/null 2>&1; then
    die "Browser demo exited. Check $LOG_DIR/browser-demo.log"
  fi
  sleep 2
done
