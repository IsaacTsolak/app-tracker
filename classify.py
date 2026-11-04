import re
from dataclasses import dataclass

from models import Status

# Phrases that mean this is not a real application update.
NOT_RELEVANT_PHRASES = [
    "new jobs",
    "job alert",
    "jobs update",
    "welcome to the job portal",
]
NEWSLETTER_SENDER_KEYWORDS = ["newsletter"]

OFFER_PHRASES = [
    "pleased to offer",
    "offer letter",
    "extend an offer",
]
REJECTION_PHRASES = [
    "unfortunately",
    "other candidates",
    "not to move forward",
    "decided not to proceed",
    "no longer under consideration",
    "not be moving forward",
    "pursue other candidates",
    "not selected",
    "position has been filled",
    "decided to move forward with",
    "will not be advancing",
]
REVIEW_SUBJECT_KEYWORDS = [
    "application",
    "applying",
    "interview",
]
INTERVIEW_PHRASES = [
    "schedule an interview",
    "schedule a call",
    "availability",
    "speak with you",
    "next round",
]
ASSESSMENT_PHRASES = [
    "assessment",
    "take-home",
    "coding challenge",
    "case study",
    "hackerrank",
    "codesignal",
]
APPLIED_PHRASES = [
    "thank you for applying",
    "application was sent",
    "received your application",
    "your application for",
]

# Up to 4 words; stop at ! . , : ; or a dash.
_COMPANY_CAPTURE = r"([^\s!.,:;\-]+(?:\s+[^\s!.,:;\-]+){0,3})"
COMPANY_PATTERNS = [
    rf"applying to {_COMPANY_CAPTURE}",
    rf"application was sent to {_COMPANY_CAPTURE}",
    rf"application to {_COMPANY_CAPTURE}",
    rf"interest in {_COMPANY_CAPTURE}",
    rf"position at {_COMPANY_CAPTURE}",
]
ROLE_PATTERNS = [
    r'Position\s+"([^"]+)"',
    r"for the (.+?) position",
    r"for the (.+?) role",
]

SENDER_NOISE_WORDS = [
    "via LinkedIn",
    "Recruiting",
    "Careers",
    "Talent",
    "Team",
]
ATS_DOMAINS = [
    "greenhouse",
    "lever",
    "workday",
    "ashby",
    "linkedin",
    "smartrecruiters",
]


@dataclass
class Classification:
    category: Status | None
    company: str | None
    role: str | None
    reason: str
    needs_review: bool = False


def _text(email: dict) -> str:
    return f"{email.get('subject') or ''}\n{email.get('body') or ''}"


def _first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip(" \t\"'")
            if value:
                return value
    return None


def _parse_sender(sender: str) -> tuple[str | None, str | None]:
    """Return (display name, email address) from a From header."""
    match = re.match(r'\s*"?([^"<]*?)"?\s*<([^>]+)>', sender)
    if match:
        name = match.group(1).strip() or None
        return name, match.group(2).strip()
    if "@" in sender:
        return None, sender.strip()
    return sender.strip() or None, None


def _is_ats_domain(email_addr: str | None) -> bool:
    if not email_addr or "@" not in email_addr:
        return False
    domain = email_addr.rsplit("@", 1)[1].lower()
    return any(ats in domain for ats in ATS_DOMAINS)


def _company_from_sender_name(name: str) -> str | None:
    cleaned = name
    for word in SENDER_NOISE_WORDS:
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" \t,-")
    return cleaned or None


ROLE_WORDS = ("engineer", "scientist", "developer", "analyst", "manager",
              "position", "role", "intern", "associate")


def _clean_company(name: str) -> str | None:
    cleaned = re.sub(r"\([^)]*\)", "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(".,;:!?-").strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    # Things like "the Associate Data Scientist" are roles, not companies
    if lowered.startswith("the "):
        return None
    if re.search(rf"\b({'|'.join(ROLE_WORDS)})\b", lowered):
        return None
    return cleaned


def extract_company(email: dict) -> str | None:
    # Try the subject first, then the body, and only accept a match
    # that passes the company check above
    for text in (email.get("subject") or "", email.get("body") or ""):
        match = _first_match(COMPANY_PATTERNS, text)
        if match:
            company = _clean_company(match)
            if company:
                return company
    # Fall back to the sender's name, unless it's an application system
    name, addr = _parse_sender(email.get("sender") or "")
    if _is_ats_domain(addr) or not name:
        return None
    company = _company_from_sender_name(name)
    return _clean_company(company) if company else None


def extract_role(email: dict) -> str | None:
    return _first_match(ROLE_PATTERNS, _text(email))


def _match_phrase(text: str, phrases: list[str]) -> str | None:
    lowered = text.lower()
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None


def classify(email: dict) -> Classification:
    subject_and_body = _text(email)
    sender = email.get("sender") or ""

    phrase = _match_phrase(subject_and_body, NOT_RELEVANT_PHRASES)
    if phrase:
        return Classification(None, None, None, f"not relevant: {phrase}")
    for keyword in NEWSLETTER_SENDER_KEYWORDS:
        if keyword.lower() in sender.lower():
            return Classification(
                None, None, None, f"not relevant: {keyword} in sender"
            )

    checks = [
        (OFFER_PHRASES, Status.OFFER, "offer"),
        (REJECTION_PHRASES, Status.REJECTED, "rejection"),
        (INTERVIEW_PHRASES, Status.INTERVIEWING, "interview"),
        (ASSESSMENT_PHRASES, Status.ASSESSMENT, "assessment"),
        (APPLIED_PHRASES, Status.APPLIED, "applied"),
    ]
    for phrases, status, label in checks:
        phrase = _match_phrase(subject_and_body, phrases)
        if phrase:
            return Classification(
                status,
                extract_company(email),
                extract_role(email),
                f"{label}: {phrase}",
            )

    subject = (email.get("subject") or "").lower()
    if any(keyword in subject for keyword in REVIEW_SUBJECT_KEYWORDS):
        return Classification(
            None,
            None,
            None,
            "looks job-related but no rule matched",
            needs_review=True,
        )
    return Classification(None, None, None, "no rule matched")
