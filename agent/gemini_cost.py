"""
Cost tracking for the post-call Gemini calls (transcript summary, effort
summary, AI disposition, RPC_PRP/RPC_PAY extraction) — these run as
separate direct genai.Client calls outside the LiveKit AgentSession's own
usage tracker, so agent.call_logging.estimate_cost() never saw them. The
saved `cost` field in call_logs/*.json only ever covered the live-call
STT/LLM/TTS, understating the real per-call total.

Uses a contextvar instead of threading an accumulator through every
function signature (5 files, one of them reached only indirectly via the
disposition-handler registry in agent/disposition_config.py) — each
Gemini call site just calls record_gemini_cost() after getting a
response; main.py resets the total before the post-call pipeline runs and
reads it back after, regardless of how deep a given call happened.
"""

import contextvars
import logging

logger = logging.getLogger("emily.gemini_cost")

# Official rates from https://ai.google.dev/gemini-api/docs/pricing
# (standard/paid tier), confirmed 2026-07-17.
GEMINI_PRICING = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
}

# Holds a single-element mutable list (not a float) so nested async tasks
# spawned via asyncio.gather — which each get their own shallow copy of the
# current context — still mutate the same underlying list object.
_post_call_cost: contextvars.ContextVar[list[float]] = contextvars.ContextVar("post_call_cost")


def reset_post_call_cost() -> None:
    """Call once, right before starting a call's post-call Gemini pipeline."""
    _post_call_cost.set([0.0])


def record_gemini_cost(model: str, usage_metadata) -> float:
    """Compute cost from a genai response's usage_metadata, add it to this
    call's running total (if reset_post_call_cost() was called earlier in
    this context), and return the individual call's own cost for logging."""
    pricing = GEMINI_PRICING.get(model)
    if pricing is None or usage_metadata is None:
        return 0.0
    input_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
    cost = round(
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"],
        6,
    )
    try:
        _post_call_cost.get()[0] += cost
    except LookupError:
        logger.debug("record_gemini_cost called outside a reset_post_call_cost() bracket")
    return cost


def get_post_call_cost_total() -> float:
    try:
        return round(_post_call_cost.get()[0], 6)
    except LookupError:
        return 0.0
