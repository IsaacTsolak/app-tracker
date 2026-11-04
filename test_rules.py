from classify import classify
from models import Status

cases = [
    ("Interview with Acme", "Hi Isaac, we'd love to schedule an interview next week.", Status.INTERVIEWING),
    ("Next steps: Acme", "Please complete this HackerRank coding challenge within 5 days.", Status.ASSESSMENT),
    ("Your offer from Acme", "We are pleased to offer you the role of ML Engineer.", Status.OFFER),
    ("Update from Acme", "Thank you for applying. Unfortunately, we will not be moving forward.", Status.REJECTED),
    ("Thank you for applying to Acme", "We received your application.", Status.APPLIED),
    ("Your weekly newsletter", "Top stories this week.", None),
]

passed = 0
for subject, body, expected in cases:
    c = classify({"subject": subject, "sender": "Acme <jobs@acme.com>", "body": body})
    ok = c.category == expected
    passed += ok
    print("PASS" if ok else "FAIL", "|", subject, "| got", c.category, "|", c.reason)
print(f"\n{passed}/{len(cases)} passed")