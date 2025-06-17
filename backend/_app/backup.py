import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from backend.settings.database import DATABASE_URL, BACKUP_FOLDER



def parse_database_url(db_url):
    parsed = urlparse(db_url)
    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/")
    }


db_config = parse_database_url(DATABASE_URL)


def backup_postgres():
    # Create a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{db_config['dbname']}_backup_{timestamp}.dump"

    # Ensure the backup folder exists (create if missing)
    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    # Full path to backup file
    filepath = os.path.join(BACKUP_FOLDER, filename)

    # Construct pg_dump command
    pg_dump_path = r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"  # adjust version/path
    command = [
        pg_dump_path,
        "-h", db_config["host"],
        "-p", str(db_config["port"]),
        "-U", db_config["user"],
        "-F", "c",
        "-f", filepath,
        db_config["dbname"]
    ]


    # Set password via environment variable (safer than command line)
    env = os.environ.copy()
    env["PGPASSWORD"] = db_config["password"]

    try:
        subprocess.run(command, check=True, env=env)
        print(f"[✔] Backup successful: {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"[✘] Backup failed: {e}")
