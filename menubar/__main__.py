"""Launch DoNotes menu bar app: python -m menubar"""
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from menubar.app import DoNotesMenuBarApp

if __name__ == "__main__":
    app = DoNotesMenuBarApp()
    app.run()
