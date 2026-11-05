import sqlite3
from contextlib import contextmanager
from datetime import date
from collections.abc import Iterator

from models import Application, Status

DB_PATH = "tracker.db"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_application(row: sqlite3.Row) -> Application:
    return Application(
        id=row["id"],
        company=row["company"],
        role=row["role"],
        status=Status(row["status"]),
        date_applied=date.fromisoformat(row["date_applied"]),
        last_activity=date.fromisoformat(row["last_activity"]),
        job_url=row["job_url"],
        location=row["location"],
        notes=row["notes"] or "",
    )


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                job_url TEXT,
                location TEXT,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_id TEXT PRIMARY KEY,
                processed_at TEXT,
                outcome TEXT,
                subject TEXT
            )
            """
        )


def add_application(app: Application) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO applications (
                company, role, status, date_applied, last_activity,
                job_url, location, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app.company,
                app.role,
                app.status.value,
                app.date_applied.isoformat(),
                app.last_activity.isoformat(),
                app.job_url,
                app.location,
                app.notes,
            ),
        )
        return cursor.lastrowid


def get_all() -> list[Application]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY last_activity DESC"
        ).fetchall()
    return [_row_to_application(row) for row in rows]


def update_status(app_id: int, new_status: Status, activity_date: date) -> None:
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE applications
            SET status = ?, last_activity = ?
            WHERE id = ?
            """,
            (new_status.value, activity_date.isoformat(), app_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"No application with id {app_id}")


def is_processed(email_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_emails WHERE email_id = ?",
            (email_id,),
        ).fetchone()
    return row is not None


def mark_processed(email_id: str, outcome: str, subject: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO processed_emails (email_id, processed_at, outcome, subject)
            VALUES (?, ?, ?, ?)
            """,
            (email_id, date.today().isoformat(), outcome, subject),
        )


def find_by_company(company: str) -> Application | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM applications
            WHERE LOWER(TRIM(company)) = LOWER(TRIM(?))
            ORDER BY last_activity DESC
            LIMIT 1
            """,
            (company,),
        ).fetchone()
    return _row_to_application(row) if row else None


def get_review_emails() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM processed_emails WHERE outcome = ?",
            ("review",),
        ).fetchall()
