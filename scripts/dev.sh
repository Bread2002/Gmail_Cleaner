#!/usr/bin/env bash
# Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
# Gmail Cleaner
# Last Updated: May 24th, 2026
# Description: Bash script to start both the FastAPI backend and Vite frontend in development mode.
#              Sets up a Python virtual environment for the backend if it doesn't exist.
#              Launches each in a new terminal window where possible. 

set -e  # Exit immediately on any error

# Determine project root and subdirectories
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Install dependencies for the frontend
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing npm dependencies..."
  npm install --prefix "$FRONTEND"
fi

# Define a helper function that generates an AppleScript-escaped string (for use in osascript commands)
escape_apple_script_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}

# Define a helper function that opens each command in a new terminal window, with cross-platform support
open_in_terminal() {
  local cmd="$1"
  local _pid_var="$2"

  # Support for the macOS Terminal.app
  if [ "$(uname)" = "Darwin" ]; then
    local escaped_cmd
    escaped_cmd="$(escape_apple_script_string "$cmd")"
    osascript <<OSA
tell application "Terminal"
  do script "$escaped_cmd"
end tell
OSA
    eval "$_pid_var=''"
    return 0
  fi

  # Support for various Linux terminal emulators
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

  # Fallback Operation: Run in background in this shell and return the PID
  bash -c "$cmd" &
  eval "$_pid_var=$!"  # Set the PID variable to the background process ID
  return 0
}

# Create the Python virtual environment (if it doesn't exist) and install the backend dependencies
if [ ! -f "$BACKEND/.venv/bin/python" ]; then
  echo "Creating Python virtual environment..."
  python -m venv "$BACKEND/.venv"
  "$BACKEND/.venv/bin/pip" install -e "$BACKEND" --quiet
fi

# Set the path to the Python binary in the virtual environment
if [ ! -v PYTHON_BIN ]; then
  PYTHON_BIN="$BACKEND/.venv/bin/python"
fi

# Define the commands to start the backend and frontend servers
BACKEND_CMD="cd '$BACKEND' ; \"$PYTHON_BIN\" -m uvicorn app.main:app --reload --port 8000"
FRONTEND_CMD="cd '$FRONTEND' ; npm run dev"

# Start the backend server in a new window and capture its PID (if possible)
echo "Starting the backend..."
open_in_terminal "$BACKEND_CMD" BACKEND_PID

# Start the frontend server in a new window and capture its PID (if possible)
echo "Starting the frontend..."
open_in_terminal "$FRONTEND_CMD" FRONTEND_PID

# Display instructions to the user
if [ -n "$BACKEND_PID" ] || [ -n "$FRONTEND_PID" ]; then
  echo ""; echo "Both servers are running."; echo "Press Ctrl+C to stop them..."
  trap "kill ${BACKEND_PID:-} ${FRONTEND_PID:-} 2>/dev/null; echo 'Servers stopped.'" EXIT INT TERM
  wait
else
  echo "Both servers are running in their respective terminals:";
  echo -e "Backend (Python/Uvicorn): http://localhost:8000";
  echo -e "Frontend (Vite) thttp://localhost:5173";
  echo "Close either window to stop that server...";
fi
