"""
LLM-based call transcript summary — one polished QA-analyst paragraph per
call, generated via Gemini when the session ends. Adapted from an existing
service that used "agent"/"customer" speaker labels from a webhook payload;
this repo's transcript (agent.call_logging.build_transcript) already uses
"agent"/"user" roles, so the formatter below maps to "Agent:"/"Customer:"
lines for the prompt.
"""

import logging
import os
from typing import Any

from google import genai

from agent.gemini_cost import record_gemini_cost

logger = logging.getLogger("emily.transcript_summary")

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.3

TRANSCRIPT_SUMMARY_PROMPT = """Role: You are a professional QA analyst writing a permanent customer record.

Task: Write exactly one polished paragraph summarizing the call transcript. Keep it factual, concise, and professional.

Rules:
- Start with the customer name and reference number in the form: Customer Name (Ref: Number).
- If the name is unknown, use Unknown Caller.
- If the reference number is missing, use Ref: N/A.
- Include the reason for the call, any payment or settlement discussed, any balance amount stated, and the outcome of the call.
- End with the final action taken, such as payment promised, callback scheduled, transferred, or user hung up.
- If an incoming phone number is provided, include it at the end as Caller: {number}.
- Do not use bullet points or multiple paragraphs.
- Do not invent facts not present in the transcript.
"""


def format_transcript_for_summary(transcript: list[dict[str, Any]]) -> str:
    """transcript items come from agent.call_logging.build_transcript:
    {"role": "agent" | "user", "message": str}."""
    lines = []
    for entry in transcript:
        message = entry.get("message")
        if not message:
            continue
        speaker = "Agent" if entry.get("role") == "agent" else "Customer"
        lines.append(f"{speaker}: {message}")
    return "\n".join(lines)


async def generate_transcript_summary(
    transcript: list[dict[str, Any]],
    file_number: str | None,
    debtor_name: str | None = None,
    caller_phone: str | None = None,
) -> str | None:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set — skipping transcript summary")
        return None

    formatted_transcript = format_transcript_for_summary(transcript)
    if not formatted_transcript:
        logger.warning("Empty transcript — cannot generate summary")
        return None

    customer_header = (
        f"{debtor_name} (Ref: {file_number})"
        if debtor_name and file_number
        else f"Unknown Caller (Ref: {file_number or 'N/A'})"
    )
    phone_line = f"Incoming Phone Number: {caller_phone}\n" if caller_phone else ""
    full_prompt = (
        f"{TRANSCRIPT_SUMMARY_PROMPT}\n\nCustomer: {customer_header}\n"
        f"{phone_line}\nTranscript:\n\n{formatted_transcript}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config={"temperature": GEMINI_TEMPERATURE},
        )
        cost = record_gemini_cost(GEMINI_MODEL, response.usage_metadata)
        summary = (response.text or "").strip()
        if not summary:
            logger.warning("Empty summary returned from Gemini")
            return None
        logger.info(
            "Generated transcript summary (length=%d chars, cost=$%.6f)", len(summary), cost
        )
        return summary
    except Exception:
        logger.exception("Transcript summary generation failed")
        return None
