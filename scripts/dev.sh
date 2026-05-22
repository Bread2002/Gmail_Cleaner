#!/usr/bin/env bash
# Gmail Cleaner — start both backend and frontend for local development
# Usage: bash scripts/dev.sh
# Requirements: Python 3.11+, Node 18+

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ── Backend ────────────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND/.venv/bin/python" ]; then
  echo "Creating Python virtual environment..."
  python -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/pip" install -e "$BACKEND" --quiet
fi

echo "Starting FastAPI backend on http://localhost:8000..."
cd "$BACKEND"
"$BACKEND/.venv/bin/python" -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────────────────────────
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing npm dependencies..."
  npm install --prefix "$FRONTEND"
fi

# Helper to open a command in a new terminal window where possible.
# Usage: open_in_terminal "<command>" pid_var_name
open_in_terminal() {
  local cmd="$1"
  local _pid_var="$2"

  # Windows (Git Bash / MINGW): use cmd.exe start to open a new window running bash -lc
  if command -v cmd.exe >/dev/null 2>&1 && [[ "$(uname -s)" =~ MINGW|MSYS|CYGWIN ]]; then
    cmd.exe /C start "" bash -lc "$cmd"
    eval "$_pid_var=''"
    return 0
  fi

  # macOS Terminal.app
  if [ "$(uname)" = "Darwin" ]; then
    osascript -e "tell application \"Terminal\" to do script \"$cmd\""
    eval "$_pid_var=''"
    return 0
  fi

  # Common Linux terminal emulators
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -ic "$cmd; exec bash" >/dev/null 2>&1 &
    eval "$_pid_var=''"
    return 0
  fi
  if command -v konsole >/dev/null 2>&1; then
    konsole -e bash -lc "$cmd; exec bash" >/dev/null 2>&1 &
    eval "$_pid_var=''"
    return 0
  fi
  if command -v xterm >/dev/null 2>&1; then
    xterm -hold -e bash -lc "$cmd" >/dev/null 2>&1 &
    eval "$_pid_var=''"
    return 0
  fi

  # Fallback: run in background in this shell and return the PID
  bash -c "$cmd" &
  eval "$_pid_var=$!"
  return 1
}

PYTHON_BIN="$BACKEND/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ] && [ -f "$BACKEND/.venv/Scripts/python.exe" ]; then
  PYTHON_BIN="$BACKEND/.venv/Scripts/python.exe"
fi

BACKEND_CMD="cd '$BACKEND' ; echo 'FastAPI backend starting on http://localhost:8000' ; \"$PYTHON_BIN\" -m uvicorn app.main:app --reload --port 8000"
FRONTEND_CMD="cd '$FRONTEND' ; echo 'Vite frontend starting on http://localhost:5173' ; npm run dev"

echo "Opening backend window..."
open_in_terminal "$BACKEND_CMD" BACKEND_PID

echo "Opening frontend window..."
open_in_terminal "$FRONTEND_CMD" FRONTEND_PID

if [ -n "$BACKEND_PID" ] || [ -n "$FRONTEND_PID" ]; then
  echo ""; echo "Both servers are running:"; echo "  Backend:  http://localhost:8000  (API docs: /docs)"; echo "  Frontend: http://localhost:5173"; echo ""; echo "Press Ctrl+C to stop both."
  trap "kill ${BACKEND_PID:-} ${FRONTEND_PID:-} 2>/dev/null; echo 'Servers stopped.'" EXIT INT TERM
  wait
else
  echo "Two terminal windows have been opened:";
  echo "  Backend  (Python/uvicorn): http://localhost:8000";
  echo "  Frontend (Vite):           http://localhost:5173";
  echo "Close either window to stop that server.";
fi
