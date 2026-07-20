"""
End-of-call logging — builds one JSON record per call and saves it as its
own file (call_logs/<conversation_id>.json) when the AgentSession closes.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from livekit.agents import ChatContext
from livekit.agents.metrics import AgentSessionUsage

logger = logging.getLogger("emily.call_logging")

LOG_DIR = Path(__file__).resolve().parent.parent / "call_logs"

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]")

# Gemini 2.5 Flash — official rate from https://ai.google.dev/gemini-api/docs/pricing
# (standard/paid tier, text input), confirmed 2026-07-10.
GEMINI_FLASH_INPUT_PER_1M_TOKENS = 0.30
GEMINI_FLASH_OUTPUT_PER_1M_TOKENS = 2.50

# Cartesia doesn't publish a flat per-unit rate — it sells a monthly credit
# pool (Pro plan: $5/mo for ~133 TTS minutes OR ~9h16m STT, i.e. the same
# credit pool spent entirely on one modality). These are that pool's price
# divided by its modality-specific quota, so they're the real effective
# per-minute rate on the Pro plan specifically, not a Cartesia-published
# unit price. Re-derive if the account's plan changes.
# https://www.cartesia.ai/pricing, confirmed 2026-07-10.
CARTESIA_PRO_PLAN_PRICE_USD = 5.0
CARTESIA_PRO_TTS_INCLUDED_MINUTES = 133.0
CARTESIA_PRO_STT_INCLUDED_MINUTES = 9 * 60 + 16  # 9h16m
CARTESIA_TTS_PER_MINUTE = CARTESIA_PRO_PLAN_PRICE_USD / CARTESIA_PRO_TTS_INCLUDED_MINUTES
CARTESIA_STT_PER_MINUTE = CARTESIA_PRO_PLAN_PRICE_USD / CARTESIA_PRO_STT_INCLUDED_MINUTES


def build_transcript(chat_ctx: ChatContext) -> list[dict[str, str]]:
    """{"role": "agent"|"user", "message": "..."} per turn — assistant/user
    message items only; tool calls, system prompt, and config-update items
    are excluded."""
    turns = []
    for item in chat_ctx.items:
        if item.type != "message" or item.role not in ("assistant", "user"):
            continue
        content = item.text_content
        if not content:
            continue
        turns.append(
            {
                "role": "agent" if item.role == "assistant" else "user",
                "message": content,
            }
        )
    return turns


def build_transcript_summary_fallback(transcript: list[dict[str, str]]) -> str:
    """Used only if the Gemini-based summary (agent.transcript_summary)
    fails or is unavailable — never the primary summary source."""
    if not transcript:
        return "No conversation recorded."
    last_agent_line = next(
        (t["message"] for t in reversed(transcript) if t["role"] == "agent"),
        None,
    )
    return last_agent_line or "No summary available."


def estimate_cost(usage: AgentSessionUsage | None) -> float:
    if usage is None:
        return 0.0
    cost = 0.0
    for u in usage.model_usage:
        if u.type == "llm_usage":
            cost += (u.input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_PER_1M_TOKENS
            cost += (u.output_tokens / 1_000_000) * GEMINI_FLASH_OUTPUT_PER_1M_TOKENS
        elif u.type == "stt_usage":
            cost += (u.audio_duration / 60) * CARTESIA_STT_PER_MINUTE
        elif u.type == "tts_usage":
            cost += (u.audio_duration / 60) * CARTESIA_TTS_PER_MINUTE
    return round(cost, 6)


def save_call_record(record: dict[str, Any]) -> None:
    """Writes call_logs/<conversation_id>.json — one file per call. If a
    file with that name already exists (re-run with the same room name),
    it's overwritten with the latest record."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    conversation_id = record.get("conversation_id") or "unknown"
    safe_name = _UNSAFE_FILENAME_CHARS.sub("_", str(conversation_id))
    log_file = LOG_DIR / f"{safe_name}.json"
    with log_file.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    logger.info("call record saved: %s", log_file)
