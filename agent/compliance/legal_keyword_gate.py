"""
Legal-Sensitive Keyword Detection Gate — ported verbatim from
`Legal-Sensitive Keyword Detection KB.txt`.

This is the highest-priority interrupt in the whole system: it overrides
verification, Mini-Miranda, payment/dispute flows, off-topic redirects,
and everything else. Every persona must check every caller turn against
this gate BEFORE running any other logic.
"""

import re

# Exact/partial-match trigger phrases from the source KB. Matching is
# deliberately broad (substring, case-insensitive) per the KB's own
# instruction: "Any appearance of these terms—casual or explicit—activates
# this protocol. No exceptions."
TRIGGER_KEYWORDS = [
    "lawsuit",
    "legal",
    "court",
    "sue",
    "suing",
    "litigation",
    "subpoena",
    "summons",
    "complaint",
    "deceased",
    "id theft",
    "identity theft",
    "fdcpa violation",
    "harassment",
    "i'm taking legal action",
    "i am taking legal action",
    "i will report you",
    "i will file a complaint",
]

_PATTERN = re.compile(
    r"(" + "|".join(re.escape(k) for k in TRIGGER_KEYWORDS) + r")",
    re.IGNORECASE,
)

CONTEXT_GATHERING_PROMPT = (
    "can you please elaborate on your issue so I may escalate it to the right team members"
)

NEUTRAL_ACKNOWLEDGMENTS = [
    "Thank you for explaining that.",
    "I appreciate you sharing that.",
    "Understood—thank you for the context.",
]

MANDATORY_TRANSFER_LINE = (
    "This sounds like something that needs to be reviewed by a specialist. "
    "I'm going to connect you now with our live representative who can assist "
    "you further. Please stay on the line while I transfer you."
)

RESISTANCE_HANDLING_LINE = (
    "For anything that may involve legal or escalation-related concerns, I'm "
    "required to connect you with a specialist. Please hold while I transfer you."
)


def detect_legal_sensitive_keyword(text: str) -> str | None:
    """Return the matched trigger phrase, or None if the gate is not tripped."""
    match = _PATTERN.search(text or "")
    return match.group(0) if match else None
