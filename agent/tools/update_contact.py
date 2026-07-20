"""
update_contact_channel

Endpoint: POST https://api.emily.collectco.com/emilyai/update-contact-channel
Confirmed schema (from the ElevenLabs webhook tool definition):

    Request body:
    {
        "file_number": "...",     # required
        "ph_number": "...",       # optional — new phone number
        "update_email": "..."     # optional — new email address
    }

At least one of ph_number / update_email should be provided per call —
this tool updates whichever contact field the caller actually gave.
No response `assignments` were defined on the original tool. Response
timeout on the original tool was 20s.
"""

import logging

import httpx
from livekit.agents import RunContext, function_tool

from agent.compliance.data_retrieval_check import NOT_VERIFIED_ERROR, require_verified_account
from agent.tools.api_client import _client

logger = logging.getLogger("emily.tools.update_contact")

RESPONSE_TIMEOUT = 20.0


@function_tool
async def update_contact_channel(
    context: RunContext,
    file_number: str,
    ph_number: str = "",
    update_email: str = "",
) -> dict:
    """Update the caller's phone number and/or email on file. Only call
    this after identity has been confirmed. Provide ph_number and/or
    update_email — whichever the caller actually gave."""
    if require_verified_account(context, file_number) is None:
        return NOT_VERIFIED_ERROR
    if not ph_number and not update_email:
        return {"error": "no_contact_value_provided"}

    body = {"file_number": file_number}
    if ph_number:
        body["ph_number"] = ph_number
    if update_email:
        body["update_email"] = update_email

    try:
        async with (
            context.with_filler("One moment please.", delay=1.2, interval=3.0, max_steps=2),
            _client() as client,
        ):
            resp = await client.post(
                "/update-contact-channel", json=body, timeout=RESPONSE_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("update-contact-channel failed: %s", exc)
        return {"error": "tool_failure"}
