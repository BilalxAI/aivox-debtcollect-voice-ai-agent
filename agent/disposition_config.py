"""
Disposition configuration — ported verbatim from
emily-ai-be/disposition_config.py. Registry of all disposition types and
their CollectCo payload overrides.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from agent.disposition_handlers.rpc_pay_handler import handle_rpc_pay_extraction
from agent.disposition_handlers.rpc_prp_handler import handle_rpc_prp_extraction


@dataclass
class DispositionConfig:
    disposition_type: str
    disposition_name: str
    category_name: str
    category_type: str
    action: str
    payload_overrides: Dict[str, Any]
    description: Optional[str] = None
    requires_ai_extraction: bool = False
    ai_extraction_handler: Optional[Callable] = None
    requires_phone_archive: bool = False
    note_template: Optional[str] = None
    set_caller_as_channel: bool = False


DISPOSITION_REGISTRY: Dict[str, DispositionConfig] = {

    "RPC_HANG_UP": DispositionConfig(
        disposition_type="RPC_HANG_UP",
        disposition_name="RPC - Hang Up",
        category_name="RPC - Hang Up",
        category_type="Engaged",
        action="RPC - Hang Up)",
        description="Customer hung up the call",
        payload_overrides={
            "action": "RPC - Hang Up)",
            "dispostion": "RPC - Hang Up)",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC - Hang Up",
                "categoryId": None,
                "categoryName": "RPC - Hang Up",
                "collectcoDesposition": "RPC - Hang Up)",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "412. RPC - Hang Up",
            },
        },
    ),

    "RPC_HOT": DispositionConfig(
        disposition_type="RPC_HOT",
        disposition_name="RPC HOT",
        category_name="all",
        category_type="NO RPC",
        action="HOT",
        description="Customer is hostile or threatening",
        payload_overrides={
            "action": "HOT",
            "dispostion": "HOT",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC HOT",
                "categoryId": None,
                "categoryName": "all",
                "collectcoDesposition": "HOT",
                "categoryType": "NO RPC",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "419. RPC HOT",
            },
        },
    ),

    "RPC_ALREADY_PAID": DispositionConfig(
        disposition_type="RPC_ALREADY_PAID",
        disposition_name="RPC Already Paid",
        category_name="Other",
        category_type="Engaged",
        action="Already Paid",
        description="Customer claims debt has already been paid",
        payload_overrides={
            "action": "Already Paid",
            "dispostion": "Already Paid",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC Already Paid",
                "categoryId": None,
                "categoryName": "Other",
                "collectcoDesposition": "Already Paid",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "414. RPC Already Paid",
            },
            "disputeReson": {"reason": "Already Paid", "requestValidationDocumentFlag": False},
        },
    ),

    "RPC_CALL_BACK": DispositionConfig(
        disposition_type="RPC_CALL_BACK",
        disposition_name="RPC Call back",
        category_name="Unable to Pay",
        category_type="Engaged",
        action="Follow Up",
        description="Customer requests a callback",
        payload_overrides={
            "action": "Follow Up",
            "dispostion": "Follow Up",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC Call back",
                "categoryId": None,
                "categoryName": "Unable to Pay",
                "collectcoDesposition": "Follow Up",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "416. RPC Call back",
            },
        },
    ),

    "RPC_DIS_WRONG_AMOUNT": DispositionConfig(
        disposition_type="RPC_DIS_WRONG_AMOUNT",
        disposition_name="RPC DIS - Wrong Amount",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Customer disputes the debt amount claiming it is incorrect",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "394. RPC DIS",
            },
            "disputeReson": {"reason": "Wrong Amount", "requestValidationDocumentFlag": False},
        },
    ),

    "RPC_DIS_ALREADY_PAID": DispositionConfig(
        disposition_type="RPC_DIS_ALREADY_PAID",
        disposition_name="RPC DIS - Already Paid",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Customer disputes the debt claiming it has already been paid",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "394. RPC DIS",
            },
            "disputeReson": {"reason": "Already Paid", "requestValidationDocumentFlag": False},
        },
    ),

    "RPC_DNC": DispositionConfig(
        disposition_type="RPC_DNC",
        disposition_name="RPC DNC",
        category_name="Other",
        category_type="Engaged",
        action="Do not call",
        description="RPC verified, debtor explicitly requests no further calls",
        note_template="Incoming CALL from: {phone_number} Do not call",
        set_caller_as_channel=True,
        payload_overrides={
            "action": "Do not call",
            "dispostion": "Do not call",
            "legalRequest": {"LegalDisqualificationReason": [], "Other": ""},
            "dispositionDetail": {
                "dispositionId": "600f631804eee36a00bc6c68",
                "dispositionName": "RPC DNC",
                "categoryId": None,
                "categoryName": "Other",
                "collectcoDesposition": "Do not call",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "455. RPC DNC",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_CD": DispositionConfig(
        disposition_type="RPC_CD",
        disposition_name="RPC CD",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Refuse to pay",
        description="RPC verified, debtor invokes cease and desist / demands all contact stop",
        note_template="Incoming CALL from: {phone_number} Refuse to pay",
        set_caller_as_channel=True,
        payload_overrides={
            "action": "Refuse to pay",
            "dispostion": "Refuse to pay",
            "cosRowid": 0,
            "dispositionDetail": {
                "dispositionId": "629e67dfe5dd2b446a36863d",
                "dispositionName": "RPC CD",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Refuse to pay",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "446. RPC CD",
            },
            "createForGroupFiles": True,
        },
    ),

    "NO_RPC_DNC": DispositionConfig(
        disposition_type="NO_RPC_DNC",
        disposition_name="Wrong Number",
        category_name="Unconnected",
        category_type="NO RPC",
        action="Wrong Number",
        description="RPC not verified, caller says don't call — send wrong number disposition (backend handles archive automatically)",
        note_template="Incoming CALL from: {phone_number} Wrong Number",
        set_caller_as_channel=True,
        requires_phone_archive=True,
        payload_overrides={
            "action": "Wrong Number",
            "dispostion": "Wrong Number",
            "legalRequest": {"LegalDisqualificationReason": [], "Other": ""},
            "dispositionDetail": {
                "dispositionId": "599b7db5ee2f2547285bebc1",
                "dispositionName": "Wrong Number",
                "categoryId": None,
                "categoryName": "Unconnected",
                "collectcoDesposition": "Wrong Number",
                "categoryType": "NO RPC",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "570. Wrong Number",
            },
            "createForGroupFiles": True,
        },
    ),

    "CLOSE_ACCOUNT_REFUSE_TO_PAY": DispositionConfig(
        disposition_type="CLOSE_ACCOUNT_REFUSE_TO_PAY",
        disposition_name="Close Account - Refuse to Pay",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Refuse to pay",
        description="Customer refuses to pay and account should be closed",
        payload_overrides={
            "action": "Refuse to pay",
            "dispostion": "Refuse to pay",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "Close Account",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Refuse to pay",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "395. Close Account",
            },
        },
    ),

    "RPC_REFUSE_TO_PAY": DispositionConfig(
        disposition_type="RPC_REFUSE_TO_PAY",
        disposition_name="RPC RTP",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Refuse to pay",
        description="Debtor explicitly refuses to make any payment during call",
        payload_overrides={
            "action": "Refuse to pay",
            "dispostion": "Refuse to pay",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC RTP",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Refuse to pay",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "428. RPC RTP",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_PRP": DispositionConfig(
        disposition_type="RPC_PRP",
        disposition_name="RPC PRP",
        category_name="Willing to Pay",
        category_type="Engaged",
        action="Promise",
        description="Debtor promises to make a payment (extracts promise amount and follow-up date from transcript)",
        requires_ai_extraction=True,
        ai_extraction_handler=handle_rpc_prp_extraction,
        payload_overrides={
            "action": "Promise",
            "dispostion": "Promise",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC PRP",
                "categoryId": None,
                "categoryName": "Willing to Pay",
                "collectcoDesposition": "Promise",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "424. RPC PRP",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_PAY": DispositionConfig(
        disposition_type="RPC_PAY",
        disposition_name="RPC Pay",
        category_name="Willing to Pay",
        category_type="Engaged",
        action="Promise",
        description="Debtor made a partial payment (extracts payment amount and follow-up date from transcript)",
        requires_ai_extraction=True,
        ai_extraction_handler=handle_rpc_pay_extraction,
        payload_overrides={
            "action": "Promise",
            "dispostion": "Promise",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC Pay",
                "categoryId": None,
                "categoryName": "Willing to Pay",
                "collectcoDesposition": "Promise",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "427. RPC Pay",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_DIS_IDENTITY_THEFT": DispositionConfig(
        disposition_type="RPC_DIS_IDENTITY_THEFT",
        disposition_name="RPC DIS - Identity Theft",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Debtor claims identity theft - debt is not theirs due to fraud",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "disputeReson": {"reason": "Identity Theft", "requestValidationDocumentFlag": False},
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "418. RPC DIS",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_DIS_NO_PRODUCT_SERVICE": DispositionConfig(
        disposition_type="RPC_DIS_NO_PRODUCT_SERVICE",
        disposition_name="RPC DIS - No Product/Service",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Debtor never received the product or service they were charged for",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "disputeReson": {"reason": "Did not Receive Product/Service", "requestValidationDocumentFlag": False},
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "418. RPC DIS",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_DIS_NEVER_ORDERED": DispositionConfig(
        disposition_type="RPC_DIS_NEVER_ORDERED",
        disposition_name="RPC DIS - Never Ordered",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Debtor claims they never ordered the product or service",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "disputeReson": {"reason": "Never Ordered Product/Service", "requestValidationDocumentFlag": False},
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "418. RPC DIS",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_DIS_BAD_QUALITY": DispositionConfig(
        disposition_type="RPC_DIS_BAD_QUALITY",
        disposition_name="RPC DIS - Bad Quality",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="Debtor disputes due to poor quality of product or service received",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "disputeReson": {"reason": "Bad Quality Product/Service", "requestValidationDocumentFlag": False},
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "418. RPC DIS",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_DIS_OTHER": DispositionConfig(
        disposition_type="RPC_DIS_OTHER",
        disposition_name="RPC DIS - Other",
        category_name="Unwilling to Pay",
        category_type="Engaged",
        action="Request Validation",
        description="General dispute that doesn't fit other specific categories",
        payload_overrides={
            "action": "Request Validation",
            "dispostion": "Request Validation",
            "disputeReson": {"reason": "Other", "requestValidationDocumentFlag": False},
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC DIS",
                "categoryId": None,
                "categoryName": "Unwilling to Pay",
                "collectcoDesposition": "Request Validation",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "418. RPC DIS",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_PIF": DispositionConfig(
        disposition_type="RPC_PIF",
        disposition_name="RPC PIF",
        category_name="Willing to Pay",
        category_type="Engaged",
        action="Process Payment",
        description="Debtor has made complete payment in full",
        payload_overrides={
            "action": "Process Payment",
            "dispostion": "Process Payment",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC PIF",
                "categoryId": None,
                "categoryName": "Willing to Pay",
                "collectcoDesposition": "Process Payment",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "424. RPC PIF",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_SIF": DispositionConfig(
        disposition_type="RPC_SIF",
        disposition_name="RPC SIF",
        category_name="Willing to Pay",
        category_type="Engaged",
        action="Process Payment",
        description="Debtor settles account in full by paying discounted lump sum (client approved)",
        payload_overrides={
            "action": "Process Payment",
            "dispostion": "Process Payment",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC SIF",
                "categoryId": None,
                "categoryName": "Willing to Pay",
                "collectcoDesposition": "Process Payment",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "431. RPC SIF",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_PRP_HARDSHIP": DispositionConfig(
        disposition_type="RPC_PRP_HARDSHIP",
        disposition_name="RPC PRP - Hardship plan",
        category_name="Unable to Pay",
        category_type="Engaged",
        action="Hardship",
        description="Debtor experiencing financial hardship (no job, financial crisis) but willing to pay when able",
        payload_overrides={
            "action": "Hardship",
            "dispostion": "Hardship",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC PRP - Hardship plan",
                "categoryId": None,
                "categoryName": "Unable to Pay",
                "collectcoDesposition": "Hardship",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "426. RPC PRP - Hardship plan",
            },
            "createForGroupFiles": True,
        },
    ),

    "RPC_RTV": DispositionConfig(
        disposition_type="RPC_RTV",
        disposition_name="RPC RTV",
        category_name="Other",
        category_type="Engaged",
        action="Refuse to verify",
        description="Right party confirms identity but refuses to verify profile details (zip code, DOB, etc.)",
        payload_overrides={
            "action": "Refuse to verify",
            "dispostion": "Refuse to verify",
            "dispositionDetail": {
                "dispositionId": None,
                "dispositionName": "RPC RTV",
                "categoryId": None,
                "categoryName": "Other",
                "collectcoDesposition": "Refuse to verify",
                "categoryType": "Engaged",
                "description": None,
                "forDepartment": None,
                "isActiveForRunplan": None,
                "name": "430. RPC RTV",
            },
            "createForGroupFiles": True,
        },
    ),

}


def get_disposition_config(disposition_type: str) -> Optional[DispositionConfig]:
    return DISPOSITION_REGISTRY.get(disposition_type)
