"""
Single unified Emily agent. There is exactly one Agent instance for the
whole call — no mid-call agent handoff (see agent/routing.py for why:
swapping agents forced a Gemini reconnect that crashed the LiveKit room
FFI layer). Persona logic (generic / Public Storage / GOV Citation)
lives entirely inside the one prompt file and is applied by the model
itself based on the cl_number returned by the file-lookup tool.
"""

import logging
from pathlib import Path

from livekit.agents import Agent, StopResponse, get_job_context
from livekit.agents.llm import ChatContext, ChatMessage

from agent.farewell_detector import FAREWELL_LINE, is_farewell

logger = logging.getLogger("emily.personas.base")
from agent.tools.callback_request import debtor_request_callback
from agent.tools.confirm_email import confirm_email_phonetically, get_email_on_file_phonetic
from agent.tools.end_call import end_call
from agent.tools.live_transfer import transfer_to_live_agent
from agent.tools.send_portal_link import send_portal_link
from agent.tools.update_contact import update_contact_channel
from agent.tools.user_details import get_user_details_by_file_number

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

TOOLS = [
    get_user_details_by_file_number,
    debtor_request_callback,
    update_contact_channel,
    send_portal_link,
    confirm_email_phonetically,
    get_email_on_file_phonetic,
    transfer_to_live_agent,
    end_call,
]


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


class EmilyAgent(Agent):
    """The one and only agent active for the duration of a call."""

    def __init__(self) -> None:
        instructions = load_prompt("emily_unified.md")
        super().__init__(instructions=instructions, tools=list(TOOLS))
        logger.info("EmilyAgent initialized [farewell-backstop-v2]")

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        # Deterministic backstop for ending the call: the LLM is supposed to
        # call the `end_call` tool itself on a farewell, but with
        # thinking_budget=0 it proved unreliable in testing (see
        # agent/farewell_detector.py for the history). This hook runs
        # BEFORE the LLM is invoked for this turn, so raising StopResponse
        # here skips the model entirely for a real "goodbye" — no race with
        # whatever the model might otherwise decide to do, unlike an
        # after-the-fact event listener would have.
        text = new_message.text_content
        matched = is_farewell(text)
        logger.info("on_user_turn_completed farewell-check text=%r matched=%s", text, matched)
        if not matched:
            return
        logger.info("farewell detected — ending call via backstop, bypassing LLM for this turn")
        speech_handle = self.session.say(FAREWELL_LINE)
        await speech_handle.wait_for_playout()
        get_job_context().delete_room()
        raise StopResponse()
