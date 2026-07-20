"""
Deterministic backstop for ending the call.

The prompt tells Gemini to call `end_call` on a farewell, but with
thinking_budget=0 (required to dodge the thought_signature crash — see
main.py) the model repeatedly mis-handled real "goodbye"s in testing:
sometimes as an unclear-audio filler, sometimes by pattern-matching to the
"caller repeats a request -> transfer" heuristic instead. Prompt rewrites
did not fix it reliably across turns.

Rather than keep tuning prose the model may or may not follow, this
matches the caller's own committed (final, not interim) transcript against
a fixed set of farewell phrases and ends the call directly in code —
independent of whatever the LLM decides to do with that turn. This is a
safety net on top of the `end_call` tool, not a replacement: the model
should still call `end_call` on its own for cases this regex misses.
"""

import re

_FAREWELL_PATTERN = re.compile(
    r"\b("
    r"good\s?bye"
    r"|bye"
    r"|hang up"
    r"|end (the )?(call|session)"
    r"|that'?s all"
    r"|i (have|gotta|got) to go"
    r"|talk to you later"
    r"|(i'?ll|i will) (call|talk to) you later"
    r")\b",
    re.IGNORECASE,
)

FAREWELL_LINE = "Thank you for calling, have a great day!"


def is_farewell(text: str | None) -> bool:
    if not text:
        return False
    return bool(_FAREWELL_PATTERN.search(text))
