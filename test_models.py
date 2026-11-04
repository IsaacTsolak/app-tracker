from datetime import date, timedelta
from models import Application, Status

app = Application(
    company="Coach",
    role="ML Engineer",
    status=Status.INTERVIEWING,
    date_applied=date.today() - timedelta(days=14),
    last_activity=date.today() - timedelta(days=5),
)

print(app)
print("Days since activity:", app.days_since_activity())