"""
Shared HTTP client for the emilyai API endpoints given by the user.

NOTE: exact request/response schemas for these endpoints were not
provided — the user said they'd supply them later. The shapes below are
reasonable guesses based on the KB/prompt text describing what each tool
does. Every function here is marked with a TODO where the schema needs
confirming. Do not treat this as verified against the real API.
"""

import logging
import os

import httpx

logger = logging.getLogger("emily.tools.api_client")

BASE_URL = "https://api.emily.collectco.com/emilyai"
API_TIMEOUT = 10.0


def _client() -> httpx.AsyncClient:
    headers = {}
    api_key = os.environ.get("EMILYAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.AsyncClient(base_url=BASE_URL, timeout=API_TIMEOUT, headers=headers)
