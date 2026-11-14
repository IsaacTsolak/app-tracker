from datetime import date, timedelta
from models import Application, Status
from db import init_db, add_application, get_all, update_status

init_db()

coach_id = add_application(Application(
    company="Coach", role="ML Engineer", status=Status.INTERVIEWING,
    date_applied=date.today() - timedelta(days=14),
    last_activity=date.today() - timedelta(days=5),
    notes="CTO intro call done",
))
harper_id = add_application(Application(
    company="Harper", role="Operator", status=Status.APPLIED,
    date_applied=date.today() - timedelta(days=3),
    last_activity=date.today() - timedelta(days=3),
))

update_status(harper_id, Status.INTERVIEWING, date.today())

for app in get_all():
    print(app.id, app.company, app.status.value, f"{app.days_since_activity()} days since activity")

try:
    update_status(999, Status.OFFER, date.today())
except ValueError as e:
    print("Caught expected error:", e)

from db import is_processed, mark_processed, find_by_company

mark_processed("test-email-1", "applied", "Thank you for applying to Coach")
print("Processed?", is_processed("test-email-1"), is_processed("never-seen"))
print("Found:", find_by_company("  coach "))
    