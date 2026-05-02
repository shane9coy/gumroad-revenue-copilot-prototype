#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"
export GUMROAD_MERCHANT_MODE="${GUMROAD_MERCHANT_MODE:-seeded}"

BUNDLED_PYTHON="/Users/sc/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
PROJECT_VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ -n "${GUMROAD_MERCHANT_PYTHON:-}" ]]; then
  PYTHON_BIN="$GUMROAD_MERCHANT_PYTHON"
elif [[ -x "$PROJECT_VENV_PYTHON" ]] && "$PROJECT_VENV_PYTHON" -c "import mcp" >/dev/null 2>&1; then
  PYTHON_BIN="$PROJECT_VENV_PYTHON"
elif [[ -x "$BUNDLED_PYTHON" ]] && "$BUNDLED_PYTHON" -c "import mcp" >/dev/null 2>&1; then
  PYTHON_BIN="$BUNDLED_PYTHON"
elif python3 -c "import mcp" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif [[ -x "$PROJECT_VENV_PYTHON" ]]; then
  PYTHON_BIN="$PROJECT_VENV_PYTHON"
elif [[ -x "$BUNDLED_PYTHON" ]]; then
  PYTHON_BIN="$BUNDLED_PYTHON"
else
  PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" -m gumroad_merchant.mcp_server
