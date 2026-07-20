"""
Debtor note creation — ported from emily-ai-be's process_finalized_object
step 6 (get debtor info, then create note). Attaches the best available
call summary to the debtor's CollectCo record.
"""

import logging
from datetime import datetime
from typing import Optional

import httpx

from agent.collectco_config import API_CREATE_NOTES, get_collectco_headers, get_debtor_url

logger = logging.getLogger("emily.debtor_notes")


async def create_debtor_note(file_number: str, note_text: str) -> Optional[dict]:
    headers = await get_collectco_headers()

    async with httpx.AsyncClient() as client:
        try:
            debtor_url = get_debtor_url(file_number, "MAI")
            debtor_resp = await client.get(debtor_url, headers=headers)
            if debtor_resp.status_code != 200:
                logger.warning("GetDebtor API returned %s for file_number=%s", debtor_resp.status_code, file_number)
                return None
            de_rowid = debtor_resp.json().get("deRowid")
        except Exception:
            logger.exception("GetDebtor API error for file_number=%s", file_number)
            return None

        try:
            note_payload = {
                "noteText": note_text or "No transcript summary available.",
                "opid": "EAI",
                "cDate": datetime.now().isoformat() + "Z",
                "derowid": de_rowid,
            }
            notes_resp = await client.post(API_CREATE_NOTES, json=note_payload, headers=headers)
            logger.info("Create Notes API status: %s for file_number=%s", notes_resp.status_code, file_number)
            try:
                return notes_resp.json()
            except Exception:
                return {"status_code": notes_resp.status_code, "text": notes_resp.text}
        except Exception:
            logger.exception("Create Notes API error for file_number=%s", file_number)
            return None
