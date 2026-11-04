import base64
import html
import os
import re
from datetime import datetime, timezone

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

JOB_QUERY = (
    '(application OR applying OR interview OR assessment OR '
    '"next steps" OR offer OR unfortunately OR "move forward") '
    '-from:me -category:promotions -category:social'
)


def get_service():
    """Return an authenticated Gmail API service."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _clean_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", subject).strip()


def _header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _plain_text_body(payload: dict) -> str | None:
    """Walk MIME parts and return decoded plain text, if any."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        text = _plain_text_body(part)
        if text:
            return text
    return None


def _html_text_body(payload: dict) -> str | None:
    """Walk MIME parts and return decoded HTML as plain text, if any."""
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data")
        if data:
            raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", raw)
            text = html.unescape(text)
            return re.sub(r"\s+", " ", text).strip()
    for part in payload.get("parts") or []:
        text = _html_text_body(part)
        if text:
            return text
    return None


def fetch_job_emails(days: int = 30, max_results: int = 50) -> list[dict]:
    """Fetch recent job-related emails as simple dicts."""
    service = get_service()
    query = f"newer_than:{days}d {JOB_QUERY}"
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    emails = []
    for message in result.get("messages", []):
        full = (
            service.users()
            .messages()
            .get(userId="me", id=message["id"], format="full")
            .execute()
        )
        payload = full.get("payload", {})
        headers = payload.get("headers", [])
        body = _plain_text_body(payload)
        if not body:
            body = _html_text_body(payload)
        if body:
            body = body[:2000]
        else:
            body = full.get("snippet", "")

        emails.append(
            {
                "id": full["id"],
                "subject": _clean_subject(_header(headers, "Subject")),
                "sender": _header(headers, "From"),
                "date": datetime.fromtimestamp(
                    int(full["internalDate"]) / 1000, tz=timezone.utc
                ).date(),
                "body": body,
            }
        )
    return emails
