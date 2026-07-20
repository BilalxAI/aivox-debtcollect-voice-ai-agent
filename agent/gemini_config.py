"""
Shared Gemini config for the structured-extraction calls ported from
emily-ai-be (effort summary, AI disposition, RPC_PRP/RPC_PAY extraction).
Deliberately separate from agent/main.py's conversational Gemini model
(gemini-2.5-flash) — these calls use the model/temperature emily-ai-be
uses for deterministic, schema-constrained extraction.
"""

import os

GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_TEMPERATURE = 0.0
GEMINI_RESPONSE_MIME_TYPE = "application/json"


def get_google_api_key() -> str | None:
    return os.environ.get("GOOGLE_API_KEY")
