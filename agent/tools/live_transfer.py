"""
Live-agent transfer — NOT an HTTP tool. In the source ElevenLabs workflow
this is a native SIP REFER transfer to a fixed number (+16233019527),
used identically for both the Public Storage and GOV Citation branches.

Telephony isn't wired up yet (console/Playground testing only), so this
gracefully no-ops with a clear log message when there's no SIP
participant in the room, instead of crashing. Once the Twilio trunk is
connected, replace the no-op branch with a real
`livekit.api.SIPClient.transfer_sip_participant` call (verify exact
method name/signature against the installed livekit-api version at that
time — this API has changed across SDK releases).
"""

import logging

from livekit.agents import RunContext, function_tool

logger = logging.getLogger("emily.tools.live_transfer")

LIVE_AGENT_TRANSFER_NUMBER = "+16233019527"

TRANSFER_ANNOUNCEMENT = (
    "Let me connect you with a live representative. You may experience a "
    "brief silence while I transfer you. Please stay on the line."
)


@function_tool
async def transfer_to_live_agent(context: RunContext, reason: str = "") -> dict:
    """Transfer the caller to a live human representative. Always say the
    transfer announcement out loud BEFORE calling this — never transfer
    silently."""
    room = getattr(context, "room", None)
    sip_participant = None
    if room is not None:
        for participant in getattr(room, "remote_participants", {}).values():
            if getattr(participant, "kind", None) == "sip":
                sip_participant = participant
                break

    if sip_participant is None:
        logger.warning(
            "transfer_to_live_agent called but no SIP participant is present "
            "(reason=%r) — telephony not wired up yet, no-op for console/Playground testing.",
            reason,
        )
        return {"status": "no_sip_participant", "would_transfer_to": LIVE_AGENT_TRANSFER_NUMBER}

    # TODO(telephony): once the Twilio trunk is connected, perform the
    # real SIP REFER here, e.g. via livekit.api.SIPClient.transfer_sip_participant
    # — confirm exact call shape against the installed livekit-api version.
    logger.info("Would transfer SIP participant to %s (reason=%r)", LIVE_AGENT_TRANSFER_NUMBER, reason)
    return {"status": "transfer_requested", "target": LIVE_AGENT_TRANSFER_NUMBER}
