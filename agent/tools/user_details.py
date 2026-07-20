"""
get_user_details_by_file_number

Endpoint: GET https://api.emily.collectco.com/emilyai/user-details-by-file-number?file_number=<number>
Confirmed schema (from the ElevenLabs webhook tool definition):

    Response shape (confirmed against the live endpoint):
    {
        "response": "...",
        "payload": {
            "name": "...", "first_name": "...", "email": "...", "phone": "...",
            "current_amount": "...", "last_payment": "...", "debt_summary": "...",
            "charge_date": "...", "file_Status": "...", "zip_code": "...",
            "year_of_birth": "...", "orig_creditor": "...", "client_name": "...",
            "cl_number": 123, "state": "..."
        }
    }

Response timeout on the original tool was 20s — matched here via httpx timeout.
"""

import logging

import httpx
from livekit.agents import RunContext, function_tool

from agent.compliance.data_retrieval_check import AccountRecord
from agent.italian_phonetics import to_phonetic_english
from agent.routing import classify_cl_number, route_by_cl_number
from agent.tools.api_client import BASE_URL

logger = logging.getLogger("emily.tools.user_details")

RESPONSE_TIMEOUT = 20.0


def _to_speakable_name(value: str | None) -> str | None:
    """The API returns names in ALL CAPS (e.g. "JUAN PENA RODAS"). Cartesia
    TTS treats all-caps words as acronyms and spells them out letter by
    letter ("J-U-A-N...") instead of speaking them naturally. Title-casing
    before the name ever reaches the LLM/TTS avoids that."""
    if not value:
        return value
    return value.title() if value.isupper() else value


def _to_speakable_org_name(value: str | None) -> str | None:
    """Same all-caps problem as _to_speakable_name, but creditor/client
    names can legitimately be short acronyms (e.g. "UNFCU") that SHOULD be
    spelled out letter by letter — title-casing those would make Cartesia
    say "Unfcu" as one word, which is wrong. Only title-case when the value
    is a real multi-word name (e.g. "POLIZIA MUNICIPALE DI RAVELLO");
    leave single short all-caps tokens alone so they're still spelled out
    as acronyms. Done in code rather than left to a prompt instruction
    because the LLM did not reliably re-case the raw tool output on its
    own — this guarantees it instead."""
    if not value or not value.isupper():
        return value
    if " " not in value.strip() and len(value.strip()) <= 5:
        return value
    return value.title()


@function_tool
async def get_user_details_by_file_number(context: RunContext, file_number: str) -> dict:
    """Look up the caller's account by their file/reference number. Never
    guess or fabricate any of these fields — only use what this tool
    returns. If the call fails or returns incomplete data, ask the caller
    for the file number again; do not proceed on partial data."""
    logger.info("get_user_details_by_file_number CALLED with file_number=%r", file_number)
    digits = "".join(ch for ch in file_number if ch.isdigit())
    if not digits:
        return {"error": "invalid_file_number"}

    try:
        async with (
            context.with_filler("One moment please.", delay=1.2, interval=3.0, max_steps=2),
            httpx.AsyncClient(base_url=BASE_URL, timeout=RESPONSE_TIMEOUT) as client,
        ):
            resp = await client.get(
                "/user-details-by-file-number", params={"file_number": digits}
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("user-details-by-file-number failed: %s", exc)
        return {"error": "tool_failure"}

    payload = data.get("payload") or {}

    # GOV Citation clients are always Italian municipal entities (see
    # agent/routing.py) — their orig_creditor/client_name need Italian
    # phonetic respelling, not just title-casing, or Cartesia TTS spells
    # them out letter by letter as unrecognized foreign words.
    is_gov_citation = classify_cl_number(payload.get("cl_number")) == "gov_citation"
    speakable_org_name = to_phonetic_english if is_gov_citation else _to_speakable_org_name

    record = AccountRecord(
        file_number=digits,
        full_name=_to_speakable_name(payload.get("name")),
        first_name=_to_speakable_name(payload.get("first_name")),
        email=payload.get("email"),
        phone=payload.get("phone"),
        current_amount=payload.get("current_amount"),
        last_payment=payload.get("last_payment"),
        debt_summary=payload.get("debt_summary"),
        charge_date=payload.get("charge_date"),
        file_status=payload.get("file_Status"),
        zip_code=payload.get("zip_code"),
        year_of_birth=payload.get("year_of_birth"),
        orig_creditor=speakable_org_name(payload.get("orig_creditor")),
        client_name=speakable_org_name(payload.get("client_name")),
        cl_number=payload.get("cl_number"),
        state=payload.get("state"),
    )

    if not record.is_complete():
        logger.warning("Incomplete account record for file_number=%s", digits)
        return {"error": "incomplete_record"}

    context.userdata["account"] = record
    await route_by_cl_number(context, record.cl_number)

    logger.info(
        "get_user_details_by_file_number SUCCESS file_number=%s full_name=%r",
        digits,
        record.full_name,
    )
    return {
        "full_name": record.full_name,
        "first_name": record.first_name,
        "email_on_file": (
            "on file, call get_email_on_file_phonetic to speak it — "
            "never guess or spell it from this text"
        )
        if record.email
        else None,
        "phone": record.phone,
        "current_amount": record.current_amount,
        "last_payment": record.last_payment,
        "debt_summary": record.debt_summary,
        "charge_date": record.charge_date,
        "file_status": record.file_status,
        "zip_code": record.zip_code,
        "year_of_birth": record.year_of_birth,
        "orig_creditor": record.orig_creditor,
        "client_name": record.client_name,
        "cl_number": record.cl_number,
        "state": record.state,
    }
