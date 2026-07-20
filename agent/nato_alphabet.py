"""
NATO-style phonetic alphabets — ported verbatim from
`NATO WORDS ENGLISH AND SPANISH.txt`.

Used only for spelling back the USERNAME portion of an email address
(everything before the @) letter by letter. The domain portion is
confirmed by saying the domain in full, never spelled out. The phonetic
language must match the caller's locked language — never mix.
"""

ENGLISH_NATO = {
    "A": "Alpha", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo",
    "F": "Foxtrot", "G": "Golf", "H": "Hotel", "I": "India", "J": "Juliet",
    "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November", "O": "Oscar",
    "P": "Papa", "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango",
    "U": "Uniform", "V": "Victor", "W": "Whiskey", "X": "X-ray",
    "Y": "Yankee", "Z": "Zulu",
}

SPANISH_NATO = {
    "A": "Antonio", "B": "Benito", "C": "Carmen", "D": "Domingo",
    "E": "Enrique", "F": "Francisco", "G": "Guillermo", "H": "Héctor",
    "I": "Ignacio", "J": "José", "K": "Kilo", "L": "Luis", "M": "María",
    "N": "Nicolás", "Ñ": "Ñandú", "O": "Oscar", "P": "Pedro",
    "Q": "Querido", "R": "Ramón", "S": "Santiago", "T": "Tomás",
    "U": "Ulises", "V": "Víctor", "W": "Washington", "X": "Xilófono",
    "Y": "Yolanda", "Z": "Zacarías",
}

SYMBOLS_EN = {"@": "At symbol", ".": "Dot", "-": "Dash", "_": "Underscore"}
SYMBOLS_ES = {"@": "Arroba", ".": "Punto", "-": "Guion", "_": "Guion bajo"}


def spell_username(username: str, language: str = "en") -> str:
    """Return a spoken-friendly, letter-by-letter phonetic spelling of the
    username portion of an email address (never the domain)."""
    table = SPANISH_NATO if language == "es" else ENGLISH_NATO
    symbols = SYMBOLS_ES if language == "es" else SYMBOLS_EN
    parts = []
    for ch in username:
        upper = ch.upper()
        if upper in table:
            parts.append(table[upper])
        elif ch in symbols:
            parts.append(symbols[ch])
        elif ch.isdigit():
            parts.append(ch)
        else:
            parts.append(ch)
    return ", ".join(parts)


def format_email_confirmation(email: str, language: str = "en") -> str:
    """Build the full spoken confirmation: username spelled phonetically,
    domain spoken in full (not spelled)."""
    if "@" not in email:
        return email
    username, domain = email.split("@", 1)
    spelled = spell_username(username, language)
    at_word = SYMBOLS_ES["@"] if language == "es" else SYMBOLS_EN["@"]
    return f"{spelled}, {at_word}, {domain}"
