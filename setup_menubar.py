"""
py2app setup for DoNotes menu bar app.

Build:
    .venv/bin/python setup_menubar.py py2app

Output: dist/DoNotes.app
"""
from setuptools import setup

APP = ["menubar/__main__.py"]
DATA_FILES = [
    ("resources", [
        "menubar/resources/icon_green.png",
        "menubar/resources/icon_red.png",
        "menubar/resources/icon_gray.png",
    ]),
]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "DoNotes",
        "CFBundleDisplayName": "DoNotes",
        "CFBundleIdentifier": "com.donotes.menubar",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Hide from Dock (menu bar only)
        "LSMinimumSystemVersion": "10.15",
    },
    "packages": ["rumps", "menubar"],
    "excludes": [
        "telegram", "openai", "google", "aiosqlite",
        "apscheduler", "jinja2", "thefuzz", "pydantic",
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
