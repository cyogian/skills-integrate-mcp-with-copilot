"""Database migration and seeding utility for local development."""

from __future__ import annotations

import argparse
from pathlib import Path

from db import DB_PATH, initialize_database


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Mergington SQLite database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing database file before migrating and seeding",
    )
    args = parser.parse_args()

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()

    initialize_database(Path(__file__).parent / "seed_data.json")
    print(f"Database ready at {DB_PATH}")
