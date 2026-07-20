"""
end_call — lets the LLM hang up the call itself once the caller is done,
instead of requiring someone to click "End session" in the LiveKit console.

Mirrors exactly what the console's "End session" button does: delete the
room via the LiveKit server API, which disconnects every participant and
fires the same job shutdown callback (_finalize_call_record in
agent/main.py) as a manual end. `job_ctx.delete_room()` already no-ops
safely in console/dev mode (no real room to delete), so this is also safe
to test locally.
"""

import logging

from livekit.agents import RunContext, function_tool, get_job_context

logger = logging.getLogger("emily.tools.end_call")


@function_tool
async def end_call(context: RunContext) -> None:
    """Call this the moment it's clear the conversation is over — the
    caller says goodbye/bye, thanks you and signs off, or explicitly asks
    to end the call or end the session. Always speak your farewell line
    BEFORE calling this — never hang up silently. Do not call this
    mid-conversation or while any required step (Mini-Miranda, dispute
    handling, etc.) is still incomplete."""
    logger.info("end_call CALLED — caller ended the conversation")
    # Waits for the farewell line to finish playing out before hanging up,
    # so the caller isn't cut off mid-sentence.
    await context.wait_for_playout()
    get_job_context().delete_room()
