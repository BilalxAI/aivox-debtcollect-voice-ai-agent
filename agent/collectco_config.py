"""
CollectCo API configuration — ported from emily-ai-be/config.py +
dependencies/auth.py. Credentials are kept in this file (not .env), matching
the reference project as-is.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger("emily.collectco_config")

# =====================================================
# CollectCo API base + endpoints
# =====================================================
COLLECTCO_BASE_URL = "https://alt.collectco.com/CollectcoAPIV6"

API_AUTHENTICATE = f"{COLLECTCO_BASE_URL}/api/Auth/authenticate"
API_GET_DEBTOR = f"{COLLECTCO_BASE_URL}/api/Debtor/GetDebtor"
API_GET_DEBTOR_SUMMARY_OVERVIEW = f"{COLLECTCO_BASE_URL}/api/debtor/GetDebtorSummmaryOverView"
API_CREATE_NOTES = f"{COLLECTCO_BASE_URL}/api/Debtor/CreateNotes"
API_CREATE_CONTACT_CHANNEL = f"{COLLECTCO_BASE_URL}/api/Debtor/CreateContactChanel"
API_UPDATE_DEBTOR_CHANNEL = f"{COLLECTCO_BASE_URL}/api/debtor/UpdateDebtorChanel"
API_CREATE_TICKET_CONTACT = f"{COLLECTCO_BASE_URL}/api/debtor/CreateTiketContact"

# =====================================================
# Service-account auth (matches emily-ai-be's AUTH_USERNAME/AUTH_PASSWORD)
# =====================================================
AUTH_USERNAME = "EAI"
AUTH_PASSWORD = "Qwerty!@#$%12345"

COLLECTCO_DB = "MASTER"
COLLECTCO_BASE_HEADERS = {"Content-Type": "application/json", "Db": COLLECTCO_DB}

_service_token: Optional[str] = None
_service_token_expiry: Optional[datetime] = None


def get_debtor_url(file_number: str, op_id: str = "MAI") -> str:
    return f"{API_GET_DEBTOR}/{file_number}/{op_id}"


def get_debtor_summary_overview_url(file_number: str) -> str:
    return f"{API_GET_DEBTOR_SUMMARY_OVERVIEW}/{file_number}"


async def fetch_service_token() -> str:
    """Fetch (or return cached) a service-account token from CollectCo.
    Cached for 55 minutes, same as emily-ai-be."""
    global _service_token, _service_token_expiry
    now = datetime.now()

    if _service_token and _service_token_expiry and now < _service_token_expiry:
        return _service_token

    logger.info("Fetching new CollectCo service account token")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            API_AUTHENTICATE,
            json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
            headers=COLLECTCO_BASE_HEADERS,
        )

    if response.status_code != 200:
        raise RuntimeError(f"CollectCo authentication failed: {response.status_code}")

    token = response.json().get("token")
    if not token:
        raise RuntimeError("CollectCo authentication response missing token")

    _service_token = token
    _service_token_expiry = now + timedelta(minutes=55)
    logger.info("CollectCo service account token refreshed (valid 55 minutes)")
    return token


async def get_collectco_headers() -> dict:
    token = await fetch_service_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Db": COLLECTCO_DB,
    }
