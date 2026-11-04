from gmail_client import fetch_job_emails

emails = fetch_job_emails(days=30, max_results=10)
print(f"Found {len(emails)} emails\n")
for e in emails:
    print(e["date"], "|", e["sender"], "|", e["subject"])