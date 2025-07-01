from apscheduler.schedulers.background import BackgroundScheduler
from .backup import backup_postgres


def start_scheduler():
    scheduler = BackgroundScheduler()

    # scheduler.add_job(backup_postgres, "interval", minutes=1)

    # ⏰ Schedule at 12:00 PM every day
    scheduler.add_job(backup_postgres, "cron", hour=12, minute=0)

    # ⏰ Schedule at 5:00 PM every day
    scheduler.add_job(backup_postgres, "cron", hour=17, minute=0)

    scheduler.start()
