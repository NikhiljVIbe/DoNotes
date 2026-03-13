"""DoNotes Setup Wizard — run with: python -m wizard"""

import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PORT = 8765
HOST = "127.0.0.1"


def open_browser():
    """Open the wizard in the default browser after a short delay."""
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    try:
        import uvicorn
    except ImportError:
        print("Wizard dependencies not installed. Run:")
        print('  pip install -e ".[wizard]"')
        sys.exit(1)

    print(f"\n  DoNotes Setup Wizard starting at http://{HOST}:{PORT}\n")

    # Open browser in background thread so uvicorn can start first
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "wizard.app:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
