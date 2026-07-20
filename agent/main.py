"""
Emily — LiveKit Agents worker entrypoint.

Run locally (no telephony needed):
    python -m agent.main console     # terminal mic/speaker test
    python -m agent.main dev         # connects to LiveKit Cloud, use the
                                      # Agents Playground for browser mic/speaker test

Audio pipeline: Cartesia (STT: ink-whisper) -> Gemini (standard text LLM,
NOT the Realtime/Live API) -> Cartesia (TTS: sonic-2), with Silero VAD for
turn detection.

This replaces an earlier attempt at Gemini's Realtime/Live API
(bidirectional native-audio session). That was abandoned after repeated,
intermittent 1007/1008 crashes the moment a tool call fired — confirmed as
a known, unresolved upstream bug in livekit-plugins-google's handling of
function calling for Gemini's native-audio model family (see e.g.
livekit/livekit#3679, livekit/agents#3784, livekit/agents#4545 — the
plugin sends a malformed function-call response back to Gemini, and
depending on audio-streaming timing, Gemini's server either tolerates it
or kills the session). Standard (non-realtime) LLM tool-calling is mature
and stable, so decoupling STT/LLM/TTS into three separate calls sidesteps
that bug entirely.

There is a single Agent (EmilyAgent) for the whole call — no mid-call
agent handoff. See agent/routing.py for why.
"""

import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from google.genai import types
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.voice.events import CloseEvent, SessionUsageUpdatedEvent
from livekit.plugins import cartesia, google, silero

from agent.ai_disposition import process_ai_disposition
from agent.call_logging import (
    build_transcript,
    build_transcript_summary_fallback,
    estimate_cost,
    save_call_record,
)
from agent.compliance.data_retrieval_check import AccountRecord
from agent.debtor_notes import create_debtor_note
from agent.effort_summary import generate_effort_summary
from agent.gemini_cost import get_post_call_cost_total, reset_post_call_cost
from agent.personas.base import EmilyAgent
from agent.transcript_summary import generate_transcript_summary

load_dotenv()

logger = logging.getLogger("emily.main")

GEMINI_TEXT_MODEL = "gemini-2.5-flash"
# Must be a literal "gemini-2.5" / "gemini-3"+ model string, NOT the
# "-latest" alias. livekit-plugins-google only stores/replays the
# thought_signature Gemini attaches to function-call parts when
# `_requires_thought_signatures(model)` matches those literal substrings
# (see livekit/plugins/google/llm.py). "gemini-flash-latest" doesn't match
# that regex, so the plugin silently drops the signature — but the model
# it currently resolves to demands one anyway, crashing every tool call
# with a 400 "Function call is missing a thought_signature" error right
# after the tool returns. Confirmed by reproducing the exact error with
# "gemini-flash-latest" via a raw two-turn function-call test against the
# Gemini API, and confirming it disappears with "gemini-2.5-flash" (which
# does 200 on this key — the old 404 note here was stale).

# The original ElevenLabs agent's literal default first message — used
# verbatim via session.say() below instead of letting the LLM improvise an
# opening, so the recorded-line disclosure is guaranteed word-for-word
# consistent and instant (no LLM round-trip needed for the greeting).
FIRST_MESSAGE = (
    "Thank you for calling, I'm Emily, Your AI Account Concierge, on a "
    "recorded line. Are you calling to make a payment today?"
)

CARTESIA_STT_MODEL = "ink-2"
CARTESIA_TTS_MODEL = "sonic-3"
# "Skylar - Friendly Guide" — user-selected voice.
CARTESIA_VOICE = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"

# Matches the ElevenLabs silence-timeout behavior (call ends/escalates after
# 6s of caller silence).
SILENCE_TIMEOUT_SECONDS = 6.0


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    call_start = time.time()
    latest_usage: SessionUsageUpdatedEvent | None = None

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=cartesia.STT(model=CARTESIA_STT_MODEL, language="en"),
        llm=google.LLM(
            model=GEMINI_TEXT_MODEL,
            # Disables Gemini's "thinking" mode. With it on, the model emits
            # function calls that require an echoed thought_signature on the
            # follow-up turn; the plugin doesn't round-trip that field, so
            # every tool call was crashing with a 400 "Function call is
            # missing a thought_signature" error right after the tool
            # returned. Confirmed via a raw two-turn function-call test
            # against the Gemini API directly — thinking_budget=0 avoids the
            # requirement entirely, not a plugin bug we can patch ourselves.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        tts=cartesia.TTS(model=CARTESIA_TTS_MODEL, voice=CARTESIA_VOICE, language="en"),
        userdata={},
        user_away_timeout=SILENCE_TIMEOUT_SECONDS,
    )

    close_event: CloseEvent | None = None

    @session.on("session_usage_updated")
    def _on_usage_updated(ev: SessionUsageUpdatedEvent) -> None:
        nonlocal latest_usage
        latest_usage = ev

    @session.on("close")
    def _on_close(ev: CloseEvent) -> None:
        nonlocal close_event
        close_event = ev

    async def _finalize_call_record(_shutdown_reason: str) -> None:
        # Runs as a job shutdown callback (not directly off the "close"
        # event) so the process is guaranteed to await the Gemini summary
        # call before exiting — the job otherwise tears down immediately
        # after "close" fires, which would kill an in-flight network call.
        transcript = build_transcript(session.history)
        usage = latest_usage.usage if latest_usage else None
        account: AccountRecord | None = session.userdata.get("account")

        # Tracks the post-call Gemini calls below (transcript summary,
        # effort summary, AI disposition, RPC extraction) — these run as
        # separate genai.Client calls outside the AgentSession's own usage
        # tracker, so estimate_cost(usage) below never sees them. See
        # agent/gemini_cost.py.
        reset_post_call_cost()

        summary = await generate_transcript_summary(
            transcript,
            file_number=account.file_number if account else None,
            debtor_name=account.full_name if account else None,
            caller_phone=account.phone if account else None,
        )
        if summary is None:
            summary = build_transcript_summary_fallback(transcript)

        record = {
            "conversation_id": ctx.room.name,
            "agent_id": ctx.job.id,
            "transcript": transcript,
            "transcript_summary": summary,
            "call_duration_secs": round(time.time() - call_start, 2),
            "cost": estimate_cost(usage),
            "termination_reason": close_event.reason.value if close_event else "unknown",
            "file_number": account.file_number if account else None,
            "full_name": account.full_name if account else None,
            "caller_phone": account.phone if account else None,
            "email_on_file": account.email if account else None,
            "current_amount": account.current_amount if account else None,
            "orig_creditor": account.orig_creditor if account else None,
            "state": account.state if account else None,
        }
        save_call_record(record)

        # ── Post-save pipeline (ported from emily-ai-be's process_finalized_object,
        # minus the DB-writing steps — see conversation) ────────────────────────
        file_number = account.file_number if account else None
        if not file_number:
            logger.info("No file_number for this call — skipping effort summary / disposition / note")
            post_call_cost = get_post_call_cost_total()
            record["post_call_cost"] = post_call_cost
            record["total_cost"] = round(record["cost"] + post_call_cost, 6)
            save_call_record(record)
            return

        caller_phone = account.phone if account else None

        effort_result, ai_disposition_result = await asyncio.gather(
            generate_effort_summary(file_number=file_number, transcript=transcript),
            process_ai_disposition(
                transcript=transcript,
                file_number=file_number,
                confidence_threshold=70,
                phone_number=caller_phone,
            ),
            return_exceptions=True,
        )
        if isinstance(effort_result, Exception):
            logger.exception("Effort summary raised", exc_info=effort_result)
        if isinstance(ai_disposition_result, Exception):
            logger.exception("AI disposition raised", exc_info=ai_disposition_result)

        await create_debtor_note(file_number=file_number, note_text=summary)

        # Re-save with the real total now that every post-call Gemini call
        # (including the transcript summary above) has run.
        post_call_cost = get_post_call_cost_total()
        record["post_call_cost"] = post_call_cost
        record["total_cost"] = round(record["cost"] + post_call_cost, 6)
        save_call_record(record)

    ctx.add_shutdown_callback(_finalize_call_record)

    await session.start(
        agent=EmilyAgent(),
        room=ctx.room,
    )

    # Speak the fixed opening line immediately via TTS only — no LLM
    # round-trip, so it's both instant and word-for-word consistent.
    session.say(FIRST_MESSAGE)


if __name__ == "__main__":
    # Default shutdown_process_timeout (10s) is too short for the post-call
    # pipeline (transcript summary + effort summary + AI disposition + debtor
    # note — several sequential/parallel Gemini + CollectCo calls). LiveKit
    # only logs an error and keeps waiting past the timeout rather than
    # killing the callback, but raising this avoids the noisy log line.
    #
    # AGENT_NAME is unset in production (empty string = automatic dispatch,
    # unchanged). Set it locally (e.g. AGENT_NAME=emily-local) to switch this
    # worker to explicit dispatch — it then only receives jobs specifically
    # routed to that name, so testing locally can never accidentally steal a
    # real call from (or collide with) the server worker. Route a test room
    # to it with scripts/dispatch_local_test.py.
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            shutdown_process_timeout=45.0,
            agent_name=os.getenv("AGENT_NAME", ""),
        )
    )
