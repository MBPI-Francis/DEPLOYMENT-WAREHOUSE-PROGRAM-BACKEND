"""
Background Scheduler and Database Backup Service.

Manages automated PostgreSQL database dumps on a scheduled timetable
and executes tasks in the background without blocking API endpoints.
"""

import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from apscheduler.schedulers.background import BackgroundScheduler
from core.config import settings


def _parse_database_url(db_url: str) -> dict:
    """Extracts host, port, user, password, and database name from connection URL."""
    parsed = urlparse(db_url)
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
    }


def backup_postgres():
    """
    Executes a pg_dump subprocess to create a timestamped .dump backup file.
    Runs automatically at designated times via APScheduler.
    """
    db_config = _parse_database_url(settings.DATABASE_URL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{db_config['dbname']}_backup_{timestamp}.dump"

    # Ensure destination backup directory exists
    os.makedirs(settings.BACKUP_FOLDER, exist_ok=True)
    filepath = os.path.join(settings.BACKUP_FOLDER, filename)

    command = [
        settings.PG_DUMP_PATH,
        "-h", db_config["host"],
        "-p", str(db_config["port"]),
        "-U", db_config["user"],
        "-F", "c",
        "-f", filepath,
        db_config["dbname"]
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = db_config["password"]

    try:
        subprocess.run(command, check=True, env=env)
        print(f"[✔] Database backup successful: {filepath}")
    except subprocess.CalledProcessError as err:
        print(f"[✘] Backup failed: {err}")
    except Exception as general_err:
        print(f"[✘] Unexpected backup failure: {general_err}")


def start_scheduler():
    """Starts the background task scheduler for scheduled maintenance jobs."""
    scheduler = BackgroundScheduler()

    # Scheduled daily backups at 12:00 PM and 5:00 PM
    scheduler.add_job(backup_postgres, "cron", hour=12, minute=0)
    scheduler.add_job(backup_postgres, "cron", hour=17, minute=0)

    scheduler.start()
    print("INFO: Background scheduler started successfully.")