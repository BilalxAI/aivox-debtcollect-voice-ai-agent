"""
RPC PRP (Promise to Pay) disposition handler — ported from
emily-ai-be/services/disposition_handlers/rpc_prp_handler.py. Extracts
promise amount and follow-up date from the transcript via Gemini, then
builds the dynamic payload fields for the RPC_PRP disposition.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import dateparser
import pytz
from google import genai
from pydantic import BaseModel, Field

from agent.gemini_config import GEMINI_MODEL, GEMINI_RESPONSE_MIME_TYPE, GEMINI_TEMPERATURE, get_google_api_key
from agent.gemini_cost import record_gemini_cost

logger = logging.getLogger("emily.disposition_handlers.rpc_prp_handler")


class RPCPRPExtraction(BaseModel):
    promise_amount: Optional[float] = Field(
        None,
        description="The amount debtor promised to pay (extract from phrases like 'I'll pay $500' or 'I can pay 200 dollars'). Set to null if no specific amount mentioned.",
    )
    follow_up_date_mention: Optional[str] = Field(
        None,
        description="Any date/time mention for when they'll pay or want follow-up (e.g., 'next Friday', 'in 3 days', 'tomorrow'). Set to null if no date mentioned.",
    )


RPC_PRP_EXTRACTION_PROMPT = """You are an expert debt collection call analyzer. Your task is to extract specific information about a promise to pay from the call transcript.

**IMPORTANT: Only extract information that is explicitly mentioned in the conversation.**

# What to Extract:

## 1. Promise Amount
Look for phrases where the debtor states a specific amount they will pay:
- "I'll pay $500"
- "I can pay 200 dollars"
- "I'll send you 150"
- "I promise to pay $1000"

**If no specific amount is mentioned, return null.**

## 2. Follow-up Date Mention
Look for any date/time mention related to when they'll pay or when to follow up:
- "next Friday"
- "in 3 days"
- "tomorrow"
- "after I get paid on the 15th"

**If no date is mentioned, return null.**

---

# Your Task:

Extract the promise_amount and follow_up_date_mention from the provided call transcript.

**CRITICAL RULES:**
- Only extract explicitly mentioned information
- Do NOT infer or assume amounts or dates
- If information is not in the transcript, return null
- For amounts, extract the numeric value only (e.g., 500.00, not "$500")
- For dates, return the exact phrase used (e.g., "next Friday", not a calculated date)
"""


def format_transcript_for_extraction(transcript: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{'Agent' if entry.get('role') == 'agent' else 'Customer'}: {entry.get('message', '')}"
        for entry in transcript
        if entry.get("message")
    )


async def extract_rpc_prp_data(transcript: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    api_key = get_google_api_key()
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set — skipping RPC PRP extraction")
        return None

    formatted_transcript = format_transcript_for_extraction(transcript)
    if not formatted_transcript:
        logger.warning("Empty transcript — cannot extract RPC PRP data")
        return None

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = f"{RPC_PRP_EXTRACTION_PROMPT}\n\n# Call Transcript:\n\n{formatted_transcript}"
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config={
                "response_mime_type": GEMINI_RESPONSE_MIME_TYPE,
                "response_schema": RPCPRPExtraction,
                "temperature": GEMINI_TEMPERATURE,
            },
        )
        cost = record_gemini_cost(GEMINI_MODEL, response.usage_metadata)
        result = json.loads(response.text)
        logger.info("RPC PRP extraction result: %s (cost=$%.6f)", result, cost)
        return {
            "promise_amount": result.get("promise_amount"),
            "follow_up_date_mention": result.get("follow_up_date_mention"),
        }
    except Exception:
        logger.exception("RPC PRP data extraction failed")
        return None


def calculate_followup_date(date_mention: Optional[str] = None) -> str:
    pst = pytz.timezone("America/Los_Angeles")
    now_pst = datetime.now(pst)

    if date_mention:
        parsed_date = dateparser.parse(
            date_mention,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now_pst,
                "TIMEZONE": "America/Los_Angeles",
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )
        if parsed_date:
            parsed_date = parsed_date.replace(hour=8, minute=0, second=0, microsecond=0)
            return parsed_date.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        logger.warning("Failed to parse date mention: %r — using default", date_mention)

    future_date = (now_pst + timedelta(days=3)).replace(hour=8, minute=0, second=0, microsecond=0)
    return future_date.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def handle_rpc_prp_extraction(
    transcript: list[dict[str, Any]], base_payload: dict[str, Any]
) -> dict[str, Any]:
    from agent.disposition_service import deep_merge_dicts

    try:
        extraction_result = await extract_rpc_prp_data(transcript)
        promise_amount = extraction_result.get("promise_amount") if extraction_result else None
        follow_up_date_mention = extraction_result.get("follow_up_date_mention") if extraction_result else None

        follow_up_date = calculate_followup_date(follow_up_date_mention)
        dynamic_fields = {
            "followUpCall": {
                "Promise": {"Amount": promise_amount, "Method": None},
                "FollowUpDate": follow_up_date,
                "FollowUpTime": None,
                "Priority": 99,
                "chanelNumber": None,
            }
        }
        return deep_merge_dicts(base_payload, dynamic_fields)
    except Exception:
        logger.exception("RPC PRP handler failed — returning base payload unchanged")
        return base_payload
