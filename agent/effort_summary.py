"""
Effort summary — ported from emily-ai-be/services/effort_summary_service.py.
Runs the same Gemini structured-extraction call and Client_number lookup;
the multi-server SQL insert at the end is intentionally omitted (DB
integration is deferred — see conversation).
"""

import json
import logging
from typing import Any, Literal, Optional

import httpx
from google import genai
from pydantic import BaseModel, Field

from agent.collectco_config import get_debtor_summary_overview_url, get_collectco_headers
from agent.gemini_config import GEMINI_MODEL, GEMINI_RESPONSE_MIME_TYPE, GEMINI_TEMPERATURE, get_google_api_key
from agent.gemini_cost import record_gemini_cost

logger = logging.getLogger("emily.effort_summary")

CallType = Literal[
    "Inbound", "Chats", "Inbound SMS", "Outbound SMS", "Predictive SMS",
    "Outbound Emails", "Emails", "Outbound", "outbound call",
]
DispositionType = Literal[
    "No Answer", "RPC Already Paid", "Answering Machine", "Generic Email Sent",
    "Disconnected Email Sent", "Left Voice Message", "SMS Sent", "0",
    "SMS - Blocked / Undelivered", "Email / RPC DIS", "Attorney not Available",
    "Email / RPC PRP", "Spoke with Regulators", "Call Screening App", "NIS",
    "Invalid Number", "Third Party", "Disconnected", "Missed Call", "Busy",
    "VM No Msg", "RPC Lost - Tech Issue", "Client", "Auto Reply",
    "Email / RPC Pay", "CSM Call", "test function", "Sales Call", "Attorney",
    "Call Again", "Hang up", "Outreach Email", "RPC PIF/SIF", "Switched off",
    "RPC Call back", "VM Left Msg", "Test Email", "No RPC - Tech Issue",
    "Dead air", "DNC", "Email / RPC Hot", "No-RPC", "Local Office",
    "Wrong Number", "Abandoned", "RPC Other", "Auto optoutSMS",
    "Spoke with Vendors", "Opt-out Email", "Third Party Call back",
    "RPC - Hangup before Tfr", "Dead Air Email Sent", "Ghost Call",
    "RPC PRP - Payment", "VM No Msg Email Sent", "Email / RPC RTP",
    "Client Call", "Hung-up", "Promise Test", "Not Available", "Test Pro",
    "Hang Up Email Sent", "Third Party Payment", "Spoke with Consumers",
    "Sales - Inquiry - Wrong/Disconnect", "No RPC DNC", "Spanish Speaker",
    "Connect Again", "Test Chat", "Call Screening App Email Sent",
    "Wrong Email", "SV RTP", "RPC Hot", "RPC Pay", "RPC", "Email / RPC PIF/SIF",
    "Tech Support", "SV DIS", "Operations Call", "Email / RPC Other",
    "RPC DIS", "Skip CallBack", "RPC CD", "SKP Lead", "Survey Test",
    "RPC - DIS - Won't Reactivate", "RPC - Not Interested", "SV Other",
    "SV PIF/SIF", "Test Call - IT", "RPC – Collection attempt",
    "Third Party Email Sent", "SV Pay", "SKP Call Back",
    "Appointment Scheduled", "Email Delivery Failed", "Settlement offer",
    "Employment not verified", "Second Voice", "Prospect Engaged",
]


class EffortSummary(BaseModel):
    """A detailed summary of a single debt collection attempt from a call transcript."""
    File_number: int = Field(..., description="The reference code or file number mentioned in the transcript.")
    Type: CallType = Field(..., description="The type of communication.")
    CALL: Literal["Yes", "No"] = Field(..., description="Was the call successfully connected to a person?")
    RPC_CONNECT: Literal["Yes", "No"] = Field(..., description="Was Right Party Contact established?")
    DISPOSITION: DispositionType = Field(..., description="The final outcome of the call.")
    Collected_Amount: float = Field(..., description="The final monetary amount processed, or 0.00 if no payment.")
    SMS: Literal["Yes", "No"] = Field(..., description="Was an SMS sent during this conversation?")
    Email: Literal["Yes", "No"] = Field(..., description="Was an email sent during this conversation?")


SYSTEM_PROMPT = """
You are an expert debt collection call transcript summarization engine.
Your task is to analyze the provided call transcript and extract key metrics into a single JSON object that strictly adheres to the provided JSON Schema.
- Determine the 'Type' based on who initiated the call ('User: Yeah, I'm calling...' means 'Inbound').
- 'CALL' is 'Yes' if a live human conversation occurred.
- 'RPC_CONNECT' is 'Yes' if the agent verifies the identity of the debtor.
- 'DISPOSITION' must be the single best match from the provided list. For a successful payment, 'RPC PRP - Payment' is highly appropriate.
- 'Collected_Amount' must be the final, successfully processed payment amount as a float (e.g., 720.00).
- 'SMS' should be 'Yes' only if an SMS was explicitly sent during the call.
- 'Email' should be 'Yes' only if an email (other than a mention of an *already received* email) was explicitly sent during the call.
"""


def format_transcript_for_llm(transcript: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{entry.get('role', '').capitalize()}: {entry.get('message', '')}" for entry in transcript
    )


async def generate_effort_summary(
    file_number: str, transcript: list[dict[str, str]]
) -> Optional[dict[str, Any]]:
    """Classify the call via Gemini and resolve Client_number. No DB write."""
    api_key = get_google_api_key()
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set — skipping effort summary")
        return None

    formatted_transcript = format_transcript_for_llm(transcript)
    if not formatted_transcript:
        logger.warning("Empty transcript — cannot generate effort summary")
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{SYSTEM_PROMPT}\n\nFile Number: {file_number}\n\nCall Transcript:\n\n{formatted_transcript}",
            config={
                "response_mime_type": GEMINI_RESPONSE_MIME_TYPE,
                "response_schema": EffortSummary,
                "temperature": GEMINI_TEMPERATURE,
            },
        )
        cost = record_gemini_cost(GEMINI_MODEL, response.usage_metadata)
        json_output = json.loads(response.text)
        logger.info(
            "Effort summary generated: CALL=%s RPC=%s DISPOSITION=%s cost=$%.6f",
            json_output.get("CALL"), json_output.get("RPC_CONNECT"), json_output.get("DISPOSITION"), cost,
        )
    except Exception:
        logger.exception("Effort summary generation failed")
        return None

    client_number = None
    try:
        debtor_summary_url = get_debtor_summary_overview_url(str(file_number))
        headers = await get_collectco_headers()
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            debtor_response = await http_client.get(debtor_summary_url, headers=headers)
            if debtor_response.status_code == 200:
                client_number = debtor_response.json().get("clNumber")
            else:
                logger.warning("GetDebtorSummmaryOverView returned %s", debtor_response.status_code)
    except Exception:
        logger.exception("Error fetching Client_number for effort summary")

    json_output["Client_number"] = client_number
    return json_output
