"""
Spousal vs. Non-Spousal state rules — ported verbatim from
`Spousal Non-Spousal States Knowledge Base.txt`.

Rule: if the caller's state is in ALLOWED_STATES, Emily may discuss the
account with a spouse after file-number validation. If in
NOT_ALLOWED_STATES (or unrecognized/missing), Emily must refuse and
require authorization from the account holder.
"""

ALLOWED_STATES = {
    "AK", "AL", "CA", "CO", "DE", "FL", "IN", "KS", "KY", "LA", "MD", "ME",
    "MI", "MO", "MS", "MT", "NC", "ND", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SD", "TX", "UT", "VA", "VT", "WA", "WV", "WY",
}

NOT_ALLOWED_STATES = {
    "AR", "AZ", "CT", "GA", "HI", "IA", "ID", "IL", "MA", "MN", "NE", "SC",
    "TN", "WI", "PR",
}

REFUSAL_LINE = (
    "I'm not able to discuss account details with anyone other than the "
    "account holder in this state. I'd need their authorization first."
)


def spousal_discussion_allowed(state: str | None) -> bool:
    """Default-deny: unknown/missing state is treated as NOT ALLOWED."""
    if not state:
        return False
    return state.strip().upper() in ALLOWED_STATES
