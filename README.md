# Emily — LiveKit Voice Agent

Production AI voice agent for Cedars Business Services, built on [LiveKit Agents](https://docs.livekit.io/agents/) (Python). Emily handles inbound debt-collection calls end-to-end: account lookup, identity verification, the mandatory Mini-Miranda disclosure, payment/dispute handling, and automated post-call recordkeeping — including writing a note directly onto the live CollectCo account.

## Architecture

**Audio pipeline:** Cartesia STT (`ink-2`) → Google Gemini (`gemini-2.5-flash`, standard text LLM) → Cartesia TTS (`sonic-3`), with Silero VAD for turn detection.

This is deliberately *not* Gemini's Realtime/Live API. An earlier implementation using it hit repeated, intermittent WebSocket crashes (1007/1008) the moment a tool call fired — a known, unresolved bug in `livekit-plugins-google`'s function-calling support for Gemini's native-audio model family. Decoupling STT/LLM/TTS into three separate calls sidesteps it entirely, at the cost of a small amount of turn-taking latency.

**Single agent, not multi-agent handoff.** There is one `EmilyAgent` (`agent/personas/base.py`) for the entire call. All three personas — generic, Public Storage, and GOV Citation (Italian municipal citations) — live in one unified prompt (`agent/prompts/emily_unified.md`) and are selected by the model itself based on the `cl_number` returned from account lookup. An earlier attempt at true agent-to-agent handoff was abandoned: swapping `Agent` instances mid-call forced a Gemini reconnect that reliably crashed the LiveKit room's FFI layer. See `agent/routing.py` for the full writeup.

**End-of-call pipeline** (`agent/main.py: _finalize_call_record`), mirroring the reference backend (`emily-ai-be`) minus its database-write steps:
1. Save the full transcript + an LLM-generated call summary → `call_logs/<room_name>.json`
2. Classify effort/disposition and apply it live against CollectCo
3. Write a summary note onto the live debtor account

**Deterministic backstops over prompt-only instructions.** Several behaviors turned out to be unreliable when left purely to prompt engineering with Gemini running at `thinking_budget=0` (required to avoid a separate `thought_signature` crash — see `agent/main.py`):
- **Ending the call** is decided in code (`EmilyAgent.on_user_turn_completed` in `agent/personas/base.py`), not by hoping the model calls the right tool. A regex-based farewell check runs *before* the LLM is ever invoked for that turn, so a real "goodbye" can't be misrouted into a live-transfer request.
- **Reading an email back to the caller** never lets the model see or relay the raw address. `confirm_email_phonetically` / `get_email_on_file_phonetic` (`agent/tools/confirm_email.py`) speak the NATO-phonetic confirmation directly via `session.say()` — the model only ever gets an acknowledgement, never the text to paraphrase.

## Project structure

```
agent/
  main.py                  Worker entrypoint, session wiring, end-of-call pipeline
  personas/base.py         The one EmilyAgent — tool registration, farewell backstop
  prompts/emily_unified.md Full persona logic (all three account types)
  tools/                   Function tools: account lookup, callback, portal link,
                            contact update, email confirmation, live transfer, end_call
  routing.py                cl_number → persona classification
  compliance/              Data-retrieval, language-lock, and legal-keyword policies
  disposition_*.py          Disposition registry + CollectCo payload building
  disposition_handlers/     Gemini-based RPC_PRP / RPC_PAY payment extraction
  effort_summary.py         Post-call effort/outcome classification
  ai_disposition.py         Post-call disposition classification + application
  transcript_summary.py     Post-call transcript summary
  gemini_cost.py             Cost tracking for the post-call Gemini calls
  call_logging.py            Transcript building, cost estimation, call_logs/ writer
  nato_alphabet.py            NATO phonetic spelling tables (EN/ES)
  italian_phonetics.py        Rule-based Italian→English-readable respelling
scripts/
  dispatch_local_test.py    Explicit-dispatch test room creator (local-only testing)
  test_client.html           Minimal LiveKit JS client for verifying a local test call
call_logs/                  One JSON record per completed call (git-ignored)
dockerfile / .dockerignore  Production container build
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `GOOGLE_API_KEY` (Gemini)
- `CARTESIA_API_KEY`

CollectCo service-account credentials are intentionally hardcoded in `agent/collectco_config.py` rather than `.env` (internal team decision — not meant to be handled as a rotating secret today).

## Running it

```powershell
python -m agent.main console   # terminal mic/speaker, no LiveKit room needed
python -m agent.main dev       # connects to LiveKit Cloud; use the Agents Playground
python -m agent.main start     # production mode (used by the Dockerfile's CMD)
```

## Local testing without touching production

The deployed worker runs with automatic dispatch (no `agent_name` set), so the LiveKit console's "Start session" button always reaches it. To test local code changes without any chance of colliding with production traffic:

```powershell
$env:AGENT_NAME="emily-local"
python -m agent.main dev
```
```powershell
python scripts/dispatch_local_test.py
```
This creates a room with **explicit dispatch** bound only to `emily-local`, and prints a `file://` URL to `scripts/test_client.html` — a minimal, self-contained LiveKit JS client that shows the exact room/connection state on screen. Open that URL (not the LiveKit console) to talk to your local worker.

## Deployment

`dockerfile` is a multi-stage build (Python 3.12, pip + `requirements.txt`, non-root runtime user) producing a production image whose `CMD` runs `python -m agent.main start`. `.dockerignore` keeps `.env`, `call_logs/` (caller PII), and the local `.venv` out of the image.

## Known limitations

- Telephony (SIP/Twilio trunk) is scaffolded (`.env.example` has `TWILIO_*` placeholders) but `agent/tools/live_transfer.py` currently no-ops the live-transfer path when no SIP participant is present — console/Playground testing only until the trunk is connected.
- Gemini has shown occasional "no response generated" flakiness immediately after a `transfer_to_live_agent` tool call — not yet root-caused, worth monitoring for caller-facing dead air in production.
- Per-call cost in `call_logs/*.json` (`cost` + `post_call_cost` + `total_cost`) covers Gemini + Cartesia STT/TTS only — LiveKit Cloud and Twilio telephony costs are billed and tracked separately.
