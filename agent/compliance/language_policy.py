"""
Language lock policy — ported from `LANGUAGE_POLICY.docx`.

Once the caller's language is detected from their first turn, it is
locked for the remainder of the call unless the caller explicitly
switches. No mixing English/Spanish within a turn. Spanish self-reference
must use feminine forms.
"""

FEMININE_SELF_REFERENCE_ES = ["cobradora de deudas", "representante", "asistente"]

SILENCE_PHRASES = {
    "en": [
        "I'm here whenever you're ready.",
        "Just checking if you're still on the line.",
        "Take your time — I'm not going anywhere.",
    ],
    "es": [
        "Aquí estoy cuando esté listo.",
        "Solo verificando si sigue en la línea.",
        "Tómese su tiempo, no hay prisa.",
    ],
}

HOLD_PHRASES = {
    "en": "Please hold while I take care of this for you.",
    "es": "Permítame un momento mientras reviso esto para usted.",
}

RETURN_PHRASES = {
    "en": "Thank you for waiting.",
    "es": "Gracias por esperar.",
}


class LanguageLock:
    """Tracks the locked language for a single call. Starts unlocked;
    locks on the first detected language and never auto-switches."""

    def __init__(self) -> None:
        self._locked: str | None = None

    @property
    def locked_language(self) -> str | None:
        return self._locked

    def lock_from_first_turn(self, detected_language: str) -> str:
        if self._locked is None:
            self._locked = detected_language
        return self._locked

    def explicit_switch(self, new_language: str) -> str:
        """Only call this when the caller explicitly requests a switch —
        never on accent/heuristic detection alone."""
        self._locked = new_language
        return self._locked
