#!/bin/bash
# Install DoNotes launchd agent for auto-start on macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
PLIST_SRC="$SCRIPT_DIR/com.donotes.bot.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.donotes.bot.plist"

echo "DoNotes launchd installer"
echo "========================="
echo "Project root: $PROJECT_ROOT"
echo "Python: $VENV_PYTHON"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "Create it first: python3 -m venv $PROJECT_ROOT/.venv"
    exit 1
fi

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Generate plist with actual paths
sed -e "s|VENV_PYTHON_PATH|$VENV_PYTHON|g" \
    -e "s|PROJECT_ROOT_PATH|$PROJECT_ROOT|g" \
    "$PLIST_SRC" > "$PLIST_DEST"

echo "Plist installed to: $PLIST_DEST"

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the agent
launchctl load "$PLIST_DEST"

echo "DoNotes agent loaded. It will start automatically on login."
echo "To check status: launchctl list | grep donotes"
echo "To stop: launchctl unload $PLIST_DEST"
