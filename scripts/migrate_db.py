#!/usr/bin/env python3
"""Run database migrations manually."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from src.storage.database import Database


async def main():
    print(f"Running migrations on: {settings.abs_database_path}")
    db = Database(settings.abs_database_path)
    await db.connect()
    print("Migrations complete.")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
