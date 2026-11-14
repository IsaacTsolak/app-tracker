import argparse
from collections import Counter

from classify import classify
from db import (
    add_application,
    find_by_company,
    init_db,
    is_processed,
    mark_processed,
    update_status,
)
from gmail_client import fetch_job_emails
from models import Application, Status

STAGE = {
    Status.APPLIED: 0,
    Status.ASSESSMENT: 1,
    Status.INTERVIEWING: 1,
    Status.OFFER: 2,
}


def can_transition(current: Status, new: Status) -> bool:
    if current in (Status.REJECTED, Status.WITHDRAWN):
        return False
    if new is Status.REJECTED:
        return True
    return STAGE[new] >= STAGE[current]


def _print_line(outcome: str, company: str | None, status: Status | None, subject: str) -> None:
    status_label = status.value if status else ""
    print(f"{outcome:10} | {company or '':20} | {status_label:12} | {subject}")


def sync(
    days: int = 30,
    max_results: int = 100,
    dry_run: bool = False,
    verbose: bool = True,
) -> None:
    init_db()
    emails = fetch_job_emails(days=days, max_results=max_results)
    emails.sort(key=lambda email: email["date"])

    counts: Counter[str] = Counter()
    for email in emails:
        if is_processed(email["id"]):
            counts["skipped"] += 1
            continue

        result = classify(email)
        company = result.company
        status = result.category
        subject = email["subject"]

        if status is None:
            outcome = "review" if result.needs_review else "ignored"
        elif company is None:
            outcome = "review"
        else:
            existing = find_by_company(company)
            if existing is None:
                if not dry_run:
                    add_application(
                        Application(
                            company=company,
                            role=result.role or "",
                            status=status,
                            date_applied=email["date"],
                            last_activity=email["date"],
                        )
                    )
                outcome = "created"
            elif can_transition(existing.status, status):
                activity_date = max(email["date"], existing.last_activity)
                if not dry_run:
                    update_status(existing.id, status, activity_date)
                outcome = "updated"
            else:
                outcome = "unchanged"

        if not dry_run:
            mark_processed(email["id"], outcome, subject)

        counts[outcome] += 1
        if verbose:
            _print_line(outcome, company, status, subject)

    if verbose:
        print()
    for outcome, count in counts.most_common():
        print(f"{outcome}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sync(dry_run=args.dry_run)
