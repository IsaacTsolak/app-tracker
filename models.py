from dataclasses import dataclass
from datetime import date
from enum import Enum


class Status(Enum):
    APPLIED = "applied"  # Application submitted; waiting to hear back
    ASSESSMENT = "assessment"  # Take-home, online test, or similar screening
    INTERVIEWING = "interviewing"  # In the interview process
    OFFER = "offer"  # Received an offer
    REJECTED = "rejected"  # Company declined the application
    WITHDRAWN = "withdrawn"  # You withdrew from the process


@dataclass
class Application:
    company: str
    role: str
    status: Status
    date_applied: date
    last_activity: date
    id: int | None = None
    job_url: str | None = None
    location: str | None = None
    notes: str = ""

    def days_since_activity(self) -> int:
        return (date.today() - self.last_activity).days
