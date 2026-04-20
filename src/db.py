"""SQLite-backed persistence layer for Mergington High School activities."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "mergington.sqlite3"


class ActivityNotFoundError(Exception):
    """Raised when an activity does not exist."""


class DuplicateEnrollmentError(Exception):
    """Raised when a student is already enrolled in an activity."""


class EnrollmentNotFoundError(Exception):
    """Raised when a student is not enrolled in an activity."""


class ActivityCapacityError(Exception):
    """Raised when an activity has reached maximum capacity."""


def _get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _run_migrations() -> None:
    with _get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                contact_email TEXT
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                club_id INTEGER,
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            );

            CREATE TABLE IF NOT EXISTS activity_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(activity_id, user_id),
                FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def _seed_if_empty(seed_path: Path) -> None:
    with _get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM activities").fetchone()["count"]
        if existing > 0:
            return

        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))

        conn.execute(
            """
            INSERT OR IGNORE INTO clubs(name, description, contact_email)
            VALUES (?, ?, ?)
            """,
            (
                "General Activities",
                "Default owner for seeded activities",
                "activities@mergington.edu",
            ),
        )

        club_id = conn.execute(
            "SELECT id FROM clubs WHERE name = ?", ("General Activities",)
        ).fetchone()["id"]

        for name, details in seed_data.items():
            conn.execute(
                """
                INSERT INTO activities(name, description, schedule, max_participants, club_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    details["description"],
                    details["schedule"],
                    details["max_participants"],
                    club_id,
                ),
            )
            activity_id = conn.execute(
                "SELECT id FROM activities WHERE name = ?", (name,)
            ).fetchone()["id"]

            for email in details.get("participants", []):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users(email, role)
                    VALUES (?, 'student')
                    """,
                    (email,),
                )
                user_id = conn.execute(
                    "SELECT id FROM users WHERE email = ?", (email,)
                ).fetchone()["id"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO activity_enrollments(activity_id, user_id)
                    VALUES (?, ?)
                    """,
                    (activity_id, user_id),
                )


def initialize_database(seed_path: Path) -> None:
    _run_migrations()
    _seed_if_empty(seed_path)


def fetch_activities() -> dict[str, dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                u.email AS participant_email
            FROM activities a
            LEFT JOIN activity_enrollments ae ON ae.activity_id = a.id
            LEFT JOIN users u ON u.id = ae.user_id
            ORDER BY a.name, u.email
            """
        ).fetchall()

    activity_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row["name"]
        if name not in activity_map:
            activity_map[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }

        if row["participant_email"]:
            activity_map[name]["participants"].append(row["participant_email"])

    return activity_map


def _get_or_create_user(conn: sqlite3.Connection, email: str) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO users(email, role)
        VALUES (?, 'student')
        """,
        (email,),
    )
    return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]


def signup_student(activity_name: str, email: str) -> None:
    conn = _get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        activity = conn.execute(
            """
            SELECT id, max_participants
            FROM activities
            WHERE name = ?
            """,
            (activity_name,),
        ).fetchone()

        if activity is None:
            raise ActivityNotFoundError(activity_name)

        enrolled_count = conn.execute(
            "SELECT COUNT(*) AS count FROM activity_enrollments WHERE activity_id = ?",
            (activity["id"],),
        ).fetchone()["count"]

        if enrolled_count >= activity["max_participants"]:
            raise ActivityCapacityError(activity_name)

        user_id = _get_or_create_user(conn, email)
        try:
            conn.execute(
                """
                INSERT INTO activity_enrollments(activity_id, user_id)
                VALUES (?, ?)
                """,
                (activity["id"], user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateEnrollmentError(email) from exc

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def unregister_student(activity_name: str, email: str) -> None:
    conn = _get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        activity = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()

        if activity is None:
            raise ActivityNotFoundError(activity_name)

        user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user is None:
            raise EnrollmentNotFoundError(email)

        result = conn.execute(
            """
            DELETE FROM activity_enrollments
            WHERE activity_id = ? AND user_id = ?
            """,
            (activity["id"], user["id"]),
        )

        if result.rowcount == 0:
            raise EnrollmentNotFoundError(email)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
