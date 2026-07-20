"""
send_portal_link

Endpoint: POST https://api.emily.collectco.com/emilyai/send-portal-link
Confirmed schema (from the ElevenLabs webhook tool definition):

    Request body:
    {
        "file_number": "...",      # optional (per source schema, though
                                    # in practice we always have it by this
                                    # point in the call — pass it when available)
        "de_email": "...",         # optional — the email the caller wants the link sent to
        "sent_on_email": true      # optional bool — whether the caller wants it via email
    }

This is the standalone "send me the portal link" request (separate from
the callback-scheduling flow, which handles its own portal link). Confirm
the email phonetically (NATO alphabet) before calling this.
No response `assignments` were defined on the original tool. Response
timeout on the original tool was 20s.
"""

import logging

import httpx
from livekit.agents import RunContext, function_tool

from agent.compliance.data_retrieval_check import NOT_VERIFIED_ERROR, require_verified_account
from agent.tools.api_client import _client

logger = logging.getLogger("emily.tools.send_portal_link")

RESPONSE_TIMEOUT = 20.0


@function_tool
async def send_portal_link(
    context: RunContext,
    de_email: str = "",
    use_email_on_file: bool = False,
    file_number: str = "",
    sent_on_email: bool = True,
) -> dict:
    """Send the secure customer portal link to the caller's confirmed
    email address. The email must already be phonetically confirmed with
    the caller (via confirm_email_phonetically or
    get_email_on_file_phonetic) before calling this.

    If the caller wants the link sent to a NEW email they dictated, pass
    it as de_email. If the caller wants to use the email already on file,
    set use_email_on_file=True and leave de_email blank — the address is
    pulled internally, you never need to know or repeat its raw text."""
    account = require_verified_account(context, file_number)
    if account is None:
        return NOT_VERIFIED_ERROR

    if use_email_on_file:
        if not account.email:
            return {"error": "no_email_on_file"}
        de_email = account.email
    elif not de_email:
        return {"error": "missing_email"}

    body = {"de_email": de_email, "sent_on_email": sent_on_email}
    if file_number:
        body["file_number"] = file_number

    try:
        async with (
            context.with_filler("One moment please.", delay=1.2, interval=3.0, max_steps=2),
            _client() as client,
        ):
            resp = await client.post(
                "/send-portal-link", json=body, timeout=RESPONSE_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("send-portal-link failed: %s", exc)
        return {"error": "tool_failure"}
