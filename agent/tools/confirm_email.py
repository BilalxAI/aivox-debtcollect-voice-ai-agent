"""
confirm_email_phonetically / get_email_on_file_phonetic

Deterministic replacement for asking Gemini to improvise NATO phonetic
spelling live. Same root-cause class as the end_call misfires (see
agent/farewell_detector.py): asking a thinking_budget=0 model to correctly
compose letter-by-letter NATO substitution from a two-line prompt
instruction was unreliable — but it turned out handing the model back a
`confirmation_text` string for it to relay verbatim wasn't reliable
either. It didn't leak the raw email, but it "simplified" the NATO words
back down into bare initials with periods (e.g. "Tango, Hotel, Alpha..."
became "T. H. A.") instead of speaking the string as given — a paraphrase,
not a data leak, but the caller hears the same ambiguous letters either
way.

The fix: these tools speak the confirmation themselves, directly via
session.say(), instead of returning the text as data for the model to
relay. If the model never receives the phonetic text at all, it has
nothing left to paraphrase — it only gets an ack telling it the line has
already been spoken, so it should move straight to asking for
confirmation instead of restating anything.
"""

import logging

from livekit.agents import RunContext, function_tool

from agent.compliance.data_retrieval_check import NOT_VERIFIED_ERROR, require_verified_account
from agent.nato_alphabet import format_email_confirmation

logger = logging.getLogger("emily.tools.confirm_email")


@function_tool
async def confirm_email_phonetically(
    context: RunContext, email: str, language: str = "en"
) -> dict:
    """Call this the moment you have a NEW email address the caller just
    gave you, BEFORE reading it back to confirm accuracy. Pass the email
    exactly as the caller gave it, and `language` matching the call's
    locked language ("en" or "es"). This tool SPEAKS the phonetic
    confirmation itself — after it returns, do not say the email again in
    any form; just ask something like "Is that correct?" without
    restating the address.
    If the caller instead wants to use the email already on file, use
    `get_email_on_file_phonetic` instead — do not use this tool for
    that case."""
    lang = "es" if language == "es" else "en"
    confirmation_text = format_email_confirmation(email, lang)
    logger.info(
        "confirm_email_phonetically CALLED email=%r language=%r -> %r",
        email,
        lang,
        confirmation_text,
    )
    speech_handle = context.session.say(confirmation_text)
    await speech_handle.wait_for_playout()
    return {"status": "spoken — do not repeat the email, just ask if it's correct"}


@function_tool
async def get_email_on_file_phonetic(context: RunContext, language: str = "en") -> dict:
    """Call this whenever the caller asks about, or wants to use, the
    email already on file — including when they say something like "use
    the one in my file" instead of dictating a new address. This tool
    SPEAKS the phonetic confirmation itself; the raw email address is
    intentionally never given to you, so there's nothing to accidentally
    read out plainly or paraphrase. After it returns, do not say anything
    resembling the email — just ask if it's correct. `language` should
    match the call's locked language ("en" or "es")."""
    account = require_verified_account(context)
    if account is None:
        return NOT_VERIFIED_ERROR
    if not account.email:
        return {"error": "no_email_on_file"}
    lang = "es" if language == "es" else "en"
    confirmation_text = format_email_confirmation(account.email, lang)
    logger.info(
        "get_email_on_file_phonetic CALLED file_number=%s language=%r -> %r",
        account.file_number,
        lang,
        confirmation_text,
    )
    speech_handle = context.session.say(confirmation_text)
    await speech_handle.wait_for_playout()
    return {"status": "spoken — do not repeat the email, just ask if it's correct"}
