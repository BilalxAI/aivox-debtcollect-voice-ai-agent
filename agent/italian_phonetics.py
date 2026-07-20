"""
Best-effort Italian -> English-readable phonetic respelling.

Cartesia's TTS (locked to language="en") has no pronunciation entry for
genuine Italian words like "POLIZIA MUNICIPALE DI RAVELLO" — instead of
mispronouncing them, it falls back to spelling them out letter by letter.
Title-casing doesn't help here (that only fixes the ALL-CAPS-as-acronym
case for words the English model *can* pronounce).

Italian orthography is close to fully phonemic, so a rule-based respelling
into plain English-readable syllables lets the English TTS read it as
words instead of triggering the unknown-word spell-out fallback. This is
an approximation, not real IPA — good enough to stop letter-by-letter
spelling, not a pronunciation-perfect result. Only applied to GOV Citation
creditor/client names (agent/routing.py confirms these are always Italian
municipal entities); everything else is untouched.
"""


# Longest-match-first: each entry is (lowercase sequence to match, its full
# phonetic replacement including the vowel sound). Matched left-to-right so
# a matched sequence's output is never re-processed by a later rule.
_MULTI_CHAR_RULES = [
    ("chi", "kee"),
    ("che", "keh"),
    ("ghi", "ghee"),
    ("ghe", "gheh"),
    ("gli", "lyee"),
    ("gn", "ny"),
    ("sci", "shee"),
    ("sce", "sheh"),
    ("ci", "chee"),
    ("ce", "cheh"),
    ("gi", "jee"),
    ("ge", "jeh"),
    ("zz", "ts"),
    ("z", "ts"),
]

_VOWEL_RULES = {
    "a": "ah",
    "e": "eh",
    "i": "ee",
    "o": "oh",
    "u": "oo",
}


def _respell_word(word: str) -> str:
    lower = word.lower()
    out: list[str] = []
    i = 0
    n = len(lower)
    while i < n:
        matched = False
        for seq, replacement in _MULTI_CHAR_RULES:
            if lower.startswith(seq, i):
                out.append(replacement)
                i += len(seq)
                matched = True
                break
        if matched:
            continue
        ch = lower[i]
        out.append(_VOWEL_RULES.get(ch, ch))
        i += 1
    return "".join(out)


def to_phonetic_english(value: str | None) -> str | None:
    """Respell each word of an Italian name into English-readable syllables.
    Capitalizes each respelled word so it still reads as a proper noun."""
    if not value:
        return value
    words = value.strip().split()
    respelled = [_respell_word(w).capitalize() for w in words]
    return " ".join(respelled)
