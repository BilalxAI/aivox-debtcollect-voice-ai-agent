"""
Disposition service — ported from emily-ai-be/services/disposition_service.py.
Fetches deRowid, builds the CollectCo payload from the disposition registry,
and sends the live disposition/contact-channel requests.
"""

import copy
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from agent.collectco_config import (
    API_CREATE_CONTACT_CHANNEL,
    API_CREATE_TICKET_CONTACT,
    API_UPDATE_DEBTOR_CHANNEL,
    get_collectco_headers,
    get_debtor_url,
)
from agent.disposition_config import DispositionConfig, get_disposition_config
from agent.disposition_templates import BASE_DISPOSITION_PAYLOAD

logger = logging.getLogger("emily.disposition_service")


async def get_derowid(file_number: str) -> str:
    if not file_number:
        raise ValueError("file_number is required")

    debtor_url = get_debtor_url(file_number, "MAI")
    headers = await get_collectco_headers()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(debtor_url, headers=headers)

    if response.status_code != 200:
        raise httpx.HTTPError(f"GetDebtor API returned status {response.status_code}")

    de_rowid = response.json().get("deRowid")
    if not de_rowid:
        raise ValueError(f"deRowid not found in GetDebtor response for file_number: {file_number}")
    return de_rowid


def deep_merge_dicts(base: Dict, override: Dict) -> Dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def build_disposition_payload(
    disposition_config: DispositionConfig,
    derowid: str,
    file_number: str,
    phone_number: Optional[str] = None,
) -> Dict[str, Any]:
    payload = copy.deepcopy(BASE_DISPOSITION_PAYLOAD)
    payload = deep_merge_dicts(payload, disposition_config.payload_overrides)

    payload["deRowid"] = derowid
    payload["action"] = disposition_config.action

    if disposition_config.set_caller_as_channel and phone_number:
        payload["chanelNumber"] = phone_number

    if disposition_config.note_template:
        payload["note"] = disposition_config.note_template.format(phone_number=phone_number or "Unknown")

    return payload


async def send_disposition_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = await get_collectco_headers()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(API_CREATE_TICKET_CONTACT, json=payload, headers=headers)

    try:
        response_data = response.json()
    except Exception:
        response_data = response.text

    return {
        "status_code": response.status_code,
        "success": 200 <= response.status_code < 300,
        "response": response_data,
    }


async def archive_phone_number(derowid: str, phone_number: str) -> Dict[str, Any]:
    """Two-step: CreateContactChanel (ensure the number exists), then
    UpdateDebtorChanel (mark it Archived)."""
    today = datetime.now().strftime("%Y-%m-%dT00:00:00")
    headers = await get_collectco_headers()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            create_payload = {
                "deRowid": derowid,
                "cby": "EAI",
                "position": 3,
                "phNumber": phone_number,
                "phSource": 2,
                "activeType": "Verified",
                "consentFlag": True,
            }
            create_response = await client.post(API_CREATE_CONTACT_CHANNEL, json=create_payload, headers=headers)

            if create_response.status_code not in (200, 201):
                logger.warning("CreateContactChanel returned %s — skipping archive", create_response.status_code)
                return {"success": False, "status_code": create_response.status_code, "step": "create"}

            archive_payload = {
                "deRowid": derowid,
                "phNumber": phone_number,
                "updatePhNumber": phone_number,
                "activeType": "Archived",
                "position": 2,
                "updatePosition": 2,
                "owner": 0,
                "mby": "EAI",
                "primaryCheck": True,
                "cdate": today,
                "mdate": today,
                "opDetails": {
                    "opId": "EAI",
                    "opname": "Emily Chat AI",
                    "opColor": "#4951D6",
                    "opImage": None,
                    "opInitial": "EAI",
                    "opTitle": "Emily AI Chat",
                    "opActive": True,
                },
            }
            archive_response = await client.put(API_UPDATE_DEBTOR_CHANNEL, json=archive_payload, headers=headers)
            success = 200 <= archive_response.status_code < 300
            try:
                response_data = archive_response.json()
            except Exception:
                response_data = archive_response.text

            return {"success": success, "status_code": archive_response.status_code, "response": response_data}
    except Exception as e:
        logger.exception("Error archiving phone number")
        return {"success": False, "error": str(e)}


async def process_disposition(
    file_number: str,
    disposition_type: str,
    phone_number: Optional[str] = None,
    transcript: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    disposition_config = get_disposition_config(disposition_type)
    if not disposition_config:
        raise ValueError(f"Invalid disposition_type: {disposition_type}")

    derowid = await get_derowid(file_number)
    payload = build_disposition_payload(disposition_config, derowid, file_number, phone_number)

    if disposition_config.requires_phone_archive:
        if phone_number:
            archive_result = await archive_phone_number(derowid, phone_number)
            logger.info("Phone archive result: %s", archive_result)
        else:
            logger.warning("Disposition requires phone archive but no phone_number provided — skipping")

    if disposition_config.requires_ai_extraction:
        if not transcript:
            logger.warning("Transcript not provided for AI extraction — proceeding with static payload")
        elif not disposition_config.ai_extraction_handler:
            logger.warning("No AI extraction handler configured — proceeding with static payload")
        else:
            try:
                payload = await disposition_config.ai_extraction_handler(transcript, payload)
            except Exception:
                logger.exception("AI extraction failed — proceeding with static payload")

    result = await send_disposition_request(payload)

    return {
        "success": result["success"],
        "message": (
            f"Disposition '{disposition_config.disposition_name}' processed successfully"
            if result["success"]
            else f"Disposition request failed with status {result['status_code']}"
        ),
        "status_code": result["status_code"],
        "response": result["response"],
        "disposition_type": disposition_type,
        "file_number": file_number,
    }
