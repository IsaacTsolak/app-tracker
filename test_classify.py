from gmail_client import fetch_job_emails
from classify import classify

for e in fetch_job_emails(days=180, max_results=50):
    c = classify(e)
    label = c.category.value if c.category else ("REVIEW" if c.needs_review else "not relevant")
    print(f"{label:14} | {c.company or '?':20} | {c.role or '':30} | {e['subject'][:50]}")
    print(f"{'':14}   reason: {c.reason}")