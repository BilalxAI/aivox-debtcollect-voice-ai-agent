"""
AI disposition classification — ported from
emily-ai-be/services/ai_disposition_service.py. Classifies the call
transcript into a disposition code via Gemini, then (if confidence is high
enough) applies it live via agent.disposition_service.process_disposition.
"""

import json
import logging
from typing import Any, Dict, Literal, Optional

from google import genai
from pydantic import BaseModel, Field

from agent.gemini_config import GEMINI_MODEL, GEMINI_RESPONSE_MIME_TYPE, GEMINI_TEMPERATURE, get_google_api_key
from agent.gemini_cost import record_gemini_cost

logger = logging.getLogger("emily.ai_disposition")

DispositionType = Literal[
    "RPC_HANG_UP", "RPC_HOT", "RPC_ALREADY_PAID", "RPC_CALL_BACK",
    "RPC_DIS_WRONG_AMOUNT", "RPC_DIS_ALREADY_PAID", "RPC_DIS_IDENTITY_THEFT",
    "RPC_DIS_NO_PRODUCT_SERVICE", "RPC_DIS_NEVER_ORDERED", "RPC_DIS_BAD_QUALITY",
    "RPC_DIS_OTHER", "RPC_DNC", "RPC_CD", "NO_RPC_DNC", "RPC_REFUSE_TO_PAY",
    "RPC_PRP", "RPC_PAY", "RPC_PRP_HARDSHIP", "RPC_RTV", "RPC_PIF", "RPC_SIF",
    "CLOSE_ACCOUNT_REFUSE_TO_PAY",
]


class DispositionClassification(BaseModel):
    disposition_type: Optional[DispositionType] = Field(
        None, description="The classified disposition type, or null if unclear"
    )
    confidence: int = Field(..., description="Confidence level from 0-100", ge=0, le=100)
    reasoning: str = Field(..., description="Brief explanation of why this disposition was chosen")


DISPOSITION_SYSTEM_PROMPT = """You are an expert debt collection call analyzer. Your task is to analyze the call transcript and determine the most appropriate disposition code based on how the call ended.

**IMPORTANT: Focus on the END of the call - the debtor's FINAL decision/action matters most.**

# Available Disposition Codes:

## 1. RPC_HANG_UP
**Meaning:** Right Party Contact – Hang Up
**When to use:** The correct person was reached, but they hung up during/after verification before any meaningful conversation.
**Key indicators:** "hung up", "disconnected", "ended abruptly", "no response after verification"

## 2. RPC_HOT
**Meaning:** Right Party Contact – Hot Call (Normal)
**When to use:** Call completed successfully, but no payment/dispute/promise occurred. Normal conversation that ended naturally.
**Key indicators:** "normal conversation", "no commitment", "just discussing", "ended naturally"

## 3. RPC_ALREADY_PAID
**Meaning:** Debt Already Paid
**When to use:** Debtor states they already paid the debt (informative, not argumentative)
**Key indicators:** "already paid", "paid it", "cleared the account", "made payment"

## 4. RPC_CALL_BACK
**Meaning:** Call Back Requested
**When to use:** Debtor asks to be called later (specific time or after event)
**Key indicators:** "call back", "call later", "call tomorrow", "reach out next week"

## 5. RPC_DIS_WRONG_AMOUNT
**Meaning:** Dispute – Wrong Amount
**When to use:** Debtor disputes the balance or amount claimed
**Key indicators:** "wrong amount", "not the right balance", "incorrect total", "charging too much"

## 6. RPC_DIS_ALREADY_PAID
**Meaning:** Dispute – Already Paid (Assertive)
**When to use:** Debtor disputes debt validity based on prior payment (argumentative/assertive)
**Key indicators:** "already paid" + dispute/frustration, "stop reporting it", "error in your records"

## 7. RPC_DIS_IDENTITY_THEFT
**Meaning:** Dispute – Identity Theft
**When to use:** Debtor claims the debt is fraudulent due to identity theft - they never made the charge
**Key indicators:** "identity theft", "fraud", "stolen identity", "never opened this account", "not mine", "someone used my information"

## 8. RPC_DIS_NO_PRODUCT_SERVICE
**Meaning:** Dispute – Did Not Receive Product/Service
**When to use:** Debtor claims they never received the product or service they were charged for
**Key indicators:** "never received", "didn't get", "never delivered", "no product", "no service"

## 9. RPC_DIS_NEVER_ORDERED
**Meaning:** Dispute – Never Ordered Product/Service
**When to use:** Debtor claims they never ordered or authorized the product/service
**Key indicators:** "never ordered", "didn't order", "never authorized", "never signed up"

## 10. RPC_DIS_BAD_QUALITY
**Meaning:** Dispute – Bad Quality Product/Service
**When to use:** Debtor disputes due to poor quality or defective product/service
**Key indicators:** "bad quality", "defective", "poor quality", "doesn't work", "broken"

## 11. RPC_DIS_OTHER
**Meaning:** Dispute – Other (Catch-all)
**When to use:** Debtor disputes the debt but the reason doesn't fit any specific category above
**Important:** Only use if a clear dispute exists but no specific category matches.

## 12. RPC_DNC
**Meaning:** Do Not Call (RPC Verified)
**When to use:** Right party was **VERIFIED** and explicitly requests no further phone calls
**Key indicators:** "stop calling", "never call me", "take me off your call list", "remove my numbers"
**Important:** Identity MUST be confirmed to use RPC_DNC. If never verified, use NO_RPC_DNC instead.

## 12b. RPC_CD
**Meaning:** Cease and Desist (RPC Verified)
**When to use:** Right party was **VERIFIED** and demands ALL contact stop — broader than just phone calls
**Key indicators:** "stop bothering me", "stop harassing", "leave me alone", "stop contacting me", "I will never pay this bill"
**Important:** Use ONLY when identity is fully verified. If unverified, use NO_RPC_DNC instead — do NOT use RPC_CD.

## 12c. NO_RPC_DNC
**Meaning:** Wrong Number / Non-RPC Do Not Call
**When to use:** Identity was **NOT verified** AND the caller requests no further calls OR demands all contact stop
**Important:** If the person never confirmed they are the debtor, use NO_RPC_DNC regardless of phrasing. Triggers phone archival.

## 13. RPC_REFUSE_TO_PAY
**Meaning:** Refuse to Pay (During Call)
**When to use:** Debtor explicitly refuses to make any payment during the call conversation
**Key indicators:** "refuse to pay", "not paying today", "won't make any payment", "I will never pay this"
**Important:** This is for in-call refusals, different from CLOSE_ACCOUNT_REFUSE_TO_PAY (final account closure).

## 14. RPC_PRP
**Meaning:** Promise to Pay
**When to use:** Debtor promises to make a payment (with or without specifying amount/date)
**Key indicators:** "I'll pay", "I promise to pay", "I can pay", "I will send payment"

## 15. RPC_PAY
**Meaning:** Partial Payment Made
**When to use:** Debtor has already made or is making a partial payment
**Key indicators:** "I paid", "I sent payment", "I made a payment", "just paid"
**Important:** Use for ALREADY made payments (past/present tense). Use RPC_PRP for future promises.

## 16. RPC_PRP_HARDSHIP
**Meaning:** Promise to Pay - Hardship Plan
**When to use:** Debtor experiencing financial hardship but expresses willingness to pay when situation improves
**Key indicators:** "can't pay", "no job", "lost my job", "financial crisis", "will pay when I can"

## 17. RPC_RTV
**Meaning:** Refuse to Verify
**When to use:** Right party confirms their identity (name) but refuses to verify additional profile details
**Key indicators:** "won't verify", "not giving you my information", "refuse to verify", confirmed name but refuses other details

## 18. RPC_PIF
**Meaning:** Paid in Full
**When to use:** Debtor has made complete payment during or right before the call
**Key indicators:** "paid in full", "complete payment", "paid everything", "balance cleared"

## 19. RPC_SIF
**Meaning:** Settled in Full
**When to use:** Debtor settles the account by paying a discounted lump sum amount
**Key indicators:** "settlement", "settled for less", "agreed on reduced amount", "settlement paid"
**Important:** RPC_SIF is for discounted/negotiated settlements; RPC_PIF is for 100% of the original debt.

## 20. CLOSE_ACCOUNT_REFUSE_TO_PAY
**Meaning:** Explicit Refusal to Pay (Final/Account Closure)
**When to use:** Debtor explicitly refuses to pay, ending collection entirely
**Key indicators:** "close my account" + finality, "don't owe", "close account"

---

# Your Task:

Analyze the provided call transcript and determine:
1. Which disposition code best matches how the call ended
2. Your confidence level (0-100)
3. Brief reasoning

**CRITICAL RULES:**
- Focus on the FINAL interaction - what happened at the END of the call
- If multiple situations occurred, choose based on the final outcome
- Set confidence based on how clear the disposition is (0-100)
- If unclear or low confidence, set disposition_type to null
- Provide brief reasoning for your decision
"""


def format_transcript_for_analysis(transcript: list[Dict[str, Any]]) -> str:
    return "\n".join(
        f"{'Agent' if entry.get('role') == 'agent' else 'Customer'}: {entry.get('message', '')}"
        for entry in transcript
        if entry.get("message")
    )


async def classify_disposition_from_transcript(
    transcript: list[Dict[str, Any]], confidence_threshold: int = 70
) -> Optional[Dict[str, Any]]:
    api_key = get_google_api_key()
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set — skipping disposition classification")
        return None

    formatted_transcript = format_transcript_for_analysis(transcript)
    if not formatted_transcript:
        logger.warning("Empty transcript — cannot classify disposition")
        return None

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = f"{DISPOSITION_SYSTEM_PROMPT}\n\n# Call Transcript:\n\n{formatted_transcript}"
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config={
                "response_mime_type": GEMINI_RESPONSE_MIME_TYPE,
                "response_schema": DispositionClassification,
                "temperature": GEMINI_TEMPERATURE,
            },
        )
        cost = record_gemini_cost(GEMINI_MODEL, response.usage_metadata)
        result = json.loads(response.text)
    except Exception:
        logger.exception("AI disposition classification failed")
        return None

    disposition_type = result.get("disposition_type")
    confidence = result.get("confidence", 0)
    reasoning = result.get("reasoning", "")

    if disposition_type is None or confidence < confidence_threshold:
        logger.info("Disposition classification skipped — confidence %s below threshold %s", confidence, confidence_threshold)
        return None

    logger.info(
        "Disposition classified as '%s' with %s%% confidence (cost=$%.6f): %s",
        disposition_type, confidence, cost, reasoning,
    )
    return {"disposition_type": disposition_type, "confidence": confidence, "reasoning": reasoning}


async def process_ai_disposition(
    transcript: list[Dict[str, Any]],
    file_number: str,
    confidence_threshold: int = 70,
    phone_number: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    classification = await classify_disposition_from_transcript(transcript, confidence_threshold)
    if not classification:
        return None

    from agent.disposition_service import process_disposition

    try:
        disposition_result = await process_disposition(
            file_number=file_number,
            disposition_type=classification["disposition_type"],
            transcript=transcript,
            phone_number=phone_number,
        )
    except Exception:
        logger.exception("Error applying disposition %s for file_number=%s", classification["disposition_type"], file_number)
        disposition_result = None

    return {"ai_classification": classification, "disposition_result": disposition_result}
