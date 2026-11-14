import io
from contextlib import redirect_stdout

from rich.console import Console
from rich.table import Table

from db import get_all, get_review_emails
from models import Status
from sync import sync

# How many quiet days before an application gets flagged
APPLIED_FOLLOW_UP_DAYS = 14
ACTIVE_FOLLOW_UP_DAYS = 7

# Lower number = shown first
STAGE_ORDER = {Status.OFFER: 0, Status.INTERVIEWING: 1, Status.ASSESSMENT: 1, Status.APPLIED: 2}
CLOSED = {Status.REJECTED, Status.WITHDRAWN}
COLORS = {
    Status.OFFER: "green",
    Status.INTERVIEWING: "cyan",
    Status.ASSESSMENT: "cyan",
    Status.APPLIED: "white",
    Status.REJECTED: "dim",
    Status.WITHDRAWN: "dim",
}

console = Console()


def needs_follow_up(app) -> bool:
    days = app.days_since_activity()
    if app.status == Status.APPLIED:
        return days >= APPLIED_FOLLOW_UP_DAYS
    if app.status in (Status.INTERVIEWING, Status.ASSESSMENT):
        return days >= ACTIVE_FOLLOW_UP_DAYS
    return False


def colored(status: Status) -> str:
    color = COLORS[status]
    return f"[{color}]{status.value}[/{color}]"


def show_stats(apps) -> None:
    total = len(apps)
    responded = sum(1 for a in apps if a.status != Status.APPLIED)
    rate = responded / total * 100 if total else 0
    console.print(
        f"\n[bold]{total}[/bold] applications   "
        f"[bold]{responded}[/bold] responses   "
        f"[bold]{rate:.0f}%[/bold] response rate\n"
    )


def show_active(apps) -> None:
    active = [a for a in apps if a.status in STAGE_ORDER]
    active.sort(key=lambda a: (STAGE_ORDER[a.status], a.days_since_activity()))

    table = Table(title="Active applications")
    for column in ("Company", "Role", "Status", "Applied", "Days quiet", ""):
        table.add_column(column)
    for a in active:
        flag = "[bold yellow]Follow up[/bold yellow]" if needs_follow_up(a) else ""
        table.add_row(
            a.company,
            a.role or "",
            colored(a.status),
            a.date_applied.isoformat(),
            str(a.days_since_activity()),
            flag,
        )
    console.print(table)


def show_closed(apps) -> None:
    closed = [a for a in apps if a.status in CLOSED]
    if not closed:
        return
    closed.sort(key=lambda a: a.last_activity, reverse=True)

    table = Table(title="Closed")
    for column in ("Company", "Role", "Status", "Last activity"):
        table.add_column(column)
    for a in closed:
        table.add_row(a.company, a.role or "", colored(a.status), a.last_activity.isoformat())
    console.print(table)


def show_review() -> None:
    rows = get_review_emails()
    if not rows:
        console.print("[green]Nothing to review.[/green]")
        return

    table = Table(title=f"Needs your review ({len(rows)})")
    table.add_column("Subject")
    table.add_column("Processed")
    for row in rows:
        table.add_row(row["subject"], row["processed_at"])
    console.print(table)


def main() -> None:
    with console.status("Checking your inbox..."):
        # sync() prints a line per email; capture it so the dashboard stays clean
        with redirect_stdout(io.StringIO()):
            sync(days=30, max_results=100)

    apps = get_all()
    show_stats(apps)
    show_active(apps)
    show_closed(apps)
    show_review()


if __name__ == "__main__":
    main()