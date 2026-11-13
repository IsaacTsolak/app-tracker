# App Tracker

A personal agent that reads my Gmail, figures out which emails are about my job applications, and keeps track of where each application stands.

I built it during my own job search, when keeping up with confirmations, rejections and interview invites across dozens of applications got hard to do by hand.

## How it works

1. **Read email.** `gmail_client.py` connects to Gmail through the Gmail API (OAuth) and pulls recent emails that look job-related, using a filtered search query.
2. **Classify.** `classify.py` is a rule-based classifier. It decides what kind of email it is (for example, an application confirmation, a rejection or an interview invite) and extracts the company name. Emails it can't classify confidently are marked "needs review" instead of being guessed.
3. **Store.** `db.py` saves applications in a local SQLite database. Processing is idempotent, so the same email is never counted twice, and incoming emails are matched to existing applications by company.
4. **Model.** `models.py` defines an `Application` and the set of statuses it can move through.

The classifier is rule-based on purpose: it's free to run, fast, and every decision can be traced to a specific rule. I refined the rules by testing them against my real inbox, fixing company-name extraction bugs and the order rules are checked in.

## Status

Working: the data model, SQLite storage, Gmail connection and email classifier, each with tests.

In progress: the sync step that applies each classified email to the matching application and updates its status. Planned after that: reminders for applications that need a follow-up, and a summary view of every application.

## Setup

Requires Python 3 and a Google Cloud project with the Gmail API enabled.

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create an OAuth client ID (Desktop app) in Google Cloud, download it as `credentials.json`, and put it in the project folder. The first run opens a browser to sign in, then saves `token.json`. Both files hold private credentials and are excluded by `.gitignore`, along with the local database `tracker.db`.

## Tests

Each part has its own test script:

```
python test_models.py
python test_db.py
python test_gmail.py
python test_rules.py
python test_classify.py
```

`test_gmail.py` needs your own `credentials.json` and access to a Gmail account.

## Files

| File | Purpose |
| --- | --- |
| `models.py` | Application data model and statuses |
| `db.py` | SQLite storage, duplicate-safe processing, company matching |
| `gmail_client.py` | Gmail API connection and email search |
| `classify.py` | Rule-based email classifier and company extraction |
| `test_*.py` | Tests for each part |
