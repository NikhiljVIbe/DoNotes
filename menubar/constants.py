from pathlib import Path

# Resolve project root: menubar/ -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
BOT_ENTRY = PROJECT_ROOT / "__main__.py"
PID_FILE = PROJECT_ROOT / "data" / "donotes.pid"
LOG_DIR = PROJECT_ROOT / "logs"
BOT_STDOUT_LOG = LOG_DIR / "bot_stdout.log"
BOT_STDERR_LOG = LOG_DIR / "bot_stderr.log"

# Icons
RESOURCES_DIR = Path(__file__).parent / "resources"
ICON_GREEN = str(RESOURCES_DIR / "icon_green.png")
ICON_RED = str(RESOURCES_DIR / "icon_red.png")
ICON_GRAY = str(RESOURCES_DIR / "icon_gray.png")

# App config
APP_NAME = "DoNotes"
STATUS_CHECK_INTERVAL = 5       # seconds
SHUTDOWN_TIMEOUT = 5            # seconds before SIGKILL
