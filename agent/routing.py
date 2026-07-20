"""
Client-number-based ruleset classification — ported from the ElevenLabs
workflow graph's edge conditions.

    cl_number in {10483, 10484, 175}                                -> Public Storage ruleset
    cl_number in {1826, 4886, 6437, 12596, 18262, 18263, 176}        -> GOV Citation ruleset
    otherwise                                                        -> Generic ruleset

NOTE: this used to swap the active `Agent` instance via
`session.update_agent()` (real multi-agent handoff). That was removed
after it caused a fatal FFI panic on Windows — swapping agent
instructions/tools mid-call forces the underlying Gemini Realtime
connection to reconnect, and that reconnect crashed the LiveKit room FFI
layer ("timed out waiting for ReadyForRoomEventRequest after
ConnectCallback"), killing the call after the very first tool call.

Instead, there is now a single `EmilyAgent` whose one unified prompt
(`agent/prompts/emily_unified.md`) contains all three rulesets and
branches on `cl_number` itself. This function just tags `userdata` with
the classification for tools/telemetry — it no longer swaps agents.
"""

import logging

logger = logging.getLogger("emily.routing")

PUBLIC_STORAGE_CL_NUMBERS = {10483, 10484, 175}
GOV_CITATION_CL_NUMBERS = {1826, 4886, 6437, 12596, 18262, 18263, 176}


def classify_cl_number(cl_number: int | None) -> str:
    if cl_number in PUBLIC_STORAGE_CL_NUMBERS:
        return "public_storage"
    if cl_number in GOV_CITATION_CL_NUMBERS:
        return "gov_citation"
    return "generic"


async def route_by_cl_number(context, cl_number: int | None) -> None:
    """No longer swaps agents — see module docstring. Just records the
    classification for observability."""
    classification = classify_cl_number(cl_number)
    context.userdata["account_type"] = classification
    logger.info("cl_number=%s classified as %s", cl_number, classification)
