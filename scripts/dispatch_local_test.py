"""
Explicitly dispatch a test room to your LOCAL agent worker, bypassing
automatic dispatch entirely — so this test can never land on the
production server worker (or vice versa), no matter what else is running.

How this fits together:
  - Your local worker only accepts this job if it was started with
    AGENT_NAME set to the same name passed here (see agent/main.py) —
    setting agent_name switches a worker from automatic to explicit
    dispatch, so it stops receiving any job that wasn't addressed to it
    by name.
  - The production worker's AGENT_NAME stays unset, so it keeps using
    automatic dispatch and is completely unaffected by this script.

Usage:
    1. In one terminal, start your local worker with a name:
         set AGENT_NAME=emily-local          (Windows cmd)
         $env:AGENT_NAME="emily-local"        (PowerShell)
         export AGENT_NAME=emily-local        (bash)
         python -m agent.main dev

    2. In another terminal, run this script:
         python scripts/dispatch_local_test.py

    3. Open the printed file:// URL in your browser — a minimal test page
       (scripts/test_client.html) that connects directly with this exact
       room/token, using the LiveKit JS SDK straight from a CDN. It shows
       "CONNECTED — room: <name>" and logs every event (mic published,
       track subscribed, transcripts received) right on the page. This
       replaces the public agents-playground.livekit.io — that page's
       actual connection behavior (whether it even honors ?url=&token=
       query params, or silently starts its own default sandbox
       connection instead) could never be verified from here, which made
       it impossible to rule out as the source of misrouted test calls.
       This page is fully self-contained and under our own control.

Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env, same
as the agent itself.
"""

import asyncio
import os
import secrets
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
from livekit import api

load_dotenv()

AGENT_NAME = os.getenv("AGENT_NAME", "emily-local")
TEST_CLIENT_PATH = Path(__file__).resolve().parent / "test_client.html"


async def main() -> None:
    livekit_url = os.environ["LIVEKIT_URL"]
    room_name = f"local-test-{secrets.token_hex(4)}"

    async with api.LiveKitAPI() as lk_api:
        await lk_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME)],
            )
        )

    token = (
        api.AccessToken()
        .with_identity("local-tester")
        .with_name("Local Tester")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    params = urllib.parse.urlencode({"url": livekit_url, "token": token})
    file_url = TEST_CLIENT_PATH.as_uri()
    print(f"Room:        {room_name}")
    print(f"agent_name:  {AGENT_NAME}  (must match AGENT_NAME your local worker was started with)")
    print()
    print("Open this in your browser to test:")
    print(f"{file_url}?{params}")


if __name__ == "__main__":
    asyncio.run(main())
