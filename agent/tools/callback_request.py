"""
debtor_request_callback

Endpoint: POST https://api.emily.collectco.com/emilyai/debtor-request-callback
Confirmed schema (from the ElevenLabs webhook tool definition):

    Request body:
    {
        "file_number": "...",   # required
        "co_date": "...",       # optional — user's preferred callback date
        "co_time": "..."        # optional — user's preferred callback time frame
    }

No response `assignments` were defined on the original tool, so the
response body isn't parsed into any fields — just checked for success.
Response timeout on the original tool was 20s.
"""

import logging

import httpx
from livekit.agents import RunContext, function_tool

from agent.compliance.data_retrieval_check import NOT_VERIFIED_ERROR, require_verified_account
from agent.tools.api_client import _client

logger = logging.getLogger("emily.tools.callback_request")

RESPONSE_TIMEOUT = 20.0


@function_tool
async def debtor_request_callback(
    context: RunContext,
    file_number: str,
    co_date: str = "",
    co_time: str = "",
) -> dict:
    """Arrange a callback when the caller asks someone to call them back.
    co_date and co_time are the caller's preferred date/time frame, in
    whatever natural phrasing they gave — pass through as spoken, do not
    reformat. Confirm the request was recorded to the caller after this
    returns successfully."""
    if require_verified_account(context, file_number) is None:
        return NOT_VERIFIED_ERROR

    body = {"file_number": file_number}
    if co_date:
        body["co_date"] = co_date
    if co_time:
        body["co_time"] = co_time

    try:
        async with (
            context.with_filler("One moment please.", delay=1.2, interval=3.0, max_steps=2),
            _client() as client,
        ):
            resp = await client.post(
                "/debtor-request-callback", json=body, timeout=RESPONSE_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("debtor-request-callback failed: %s", exc)
        return {"error": "tool_failure"}
