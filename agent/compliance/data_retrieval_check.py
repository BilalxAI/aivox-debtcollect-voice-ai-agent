"""
File-Number-Only Data Access Policy — ported verbatim from
`Data_retreival_check.docx`.

Core rule (non-negotiable): never use assumptions, default variables,
caller-stated values, previously stored context, or self-generated /
inferred information. All account-level data must come exclusively from
`get_user_details_by_file_number`. If a field isn't returned by that
tool, it does not exist as far as the agent is concerned.
"""

from dataclasses import dataclass

RETRY_PHRASES = [
    "I'm not able to pull up the account with that file number. Could you please confirm or re-provide it?",
    "It looks like I couldn't retrieve the details. Let's try again—what is the file number?",
    "I'm unable to access the account right now. Please share the file number once more so I can pull the correct information.",
]

ASK_FOR_FILE_NUMBER = (
    "To continue, I'll need the file number so I can pull up the account."
)

REQUIRED_FIELDS = ("full_name", "orig_creditor", "current_amount", "cl_number")


@dataclass
class AccountRecord:
    file_number: str
    full_name: str | None = None
    first_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_amount: str | None = None
    last_payment: str | None = None
    debt_summary: str | None = None
    charge_date: str | None = None
    file_status: str | None = None
    zip_code: str | None = None
    year_of_birth: str | None = None
    orig_creditor: str | None = None
    client_name: str | None = None
    cl_number: int | None = None
    state: str | None = None

    def is_complete(self) -> bool:
        """A record is only usable once every required field is present.
        Never proceed on a partially-populated record — ask for the file
        number again instead per the source policy's retry rule."""
        return all(getattr(self, field) not in (None, "") for field in REQUIRED_FIELDS)


NOT_VERIFIED_ERROR = {
    "error": "account_not_verified",
    "instruction": (
        "You must call get_user_details_by_file_number successfully in this "
        "call before using this tool. Do not answer, confirm, or speak as if "
        "this succeeded — call get_user_details_by_file_number now."
    ),
}


def require_verified_account(context, file_number: str | None = None) -> AccountRecord | None:
    """Code-level guardrail (not just a prompt instruction): every tool
    that touches account data must call this first. If
    get_user_details_by_file_number hasn't been successfully called yet
    in this session — or was called for a different file number — this
    returns None, and the caller should return NOT_VERIFIED_ERROR instead
    of proceeding. This is what actually prevents fabrication: the model
    can *claim* it looked something up, but the underlying tool call will
    hard-fail with an instruction to call the lookup tool for real."""
    account: AccountRecord | None = context.userdata.get("account")
    if account is None:
        return None
    if file_number:
        digits = "".join(ch for ch in file_number if ch.isdigit())
        if digits and digits != account.file_number:
            return None
    return account
