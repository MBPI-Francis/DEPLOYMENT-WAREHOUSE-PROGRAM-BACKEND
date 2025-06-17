from apscheduler.schedulers.background import BackgroundScheduler
from .backup import backup_postgres


def start_scheduler():
    scheduler = BackgroundScheduler()
    # scheduler.add_job(backup_postgres, "cron", hour=0, minute=0)  # Daily at 12:00AM
    scheduler.add_job(backup_postgres, "interval", minutes=1)
    scheduler.start()
