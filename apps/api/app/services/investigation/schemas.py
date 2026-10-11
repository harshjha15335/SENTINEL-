"""The structured output of an investigation. The same schema holds AI and deterministic output.

Every fact and indicator cites the records it rests on (``SourceRef``). The server rejects any
citation to a record that the run did not retrieve through its tools.
"""

import uuid
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceKind(StrEnum):
    CASE = "case"
    TRANSACTION = "transaction"
    RISK_ASSESSMENT = "risk_assessment"
    PAYMENT_EVENT = "payment_event"
    CASE_NOTE = "case_note"
    EVIDENCE = "evidence"
    PAYER_HISTORY = "payer_history"


class RecommendedAction(StrEnum):
    NO_FURTHER_ACTION = "NO_FURTHER_ACTION"
    CONTINUE_MANUAL_REVIEW = "CONTINUE_MANUAL_REVIEW"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    PREPARE_EVIDENCE_PACKET = "PREPARE_EVIDENCE_PACKET"
    CONSIDER_REFUND = "CONSIDER_REFUND"
    ESCALATE = "ESCALATE"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(_Strict):
    kind: SourceKind = Field(description="Type of record cited.")
    id: str = Field(
        description="The record id exactly as returned by a tool in this investigation.",
        max_length=64,
    )


class VerifiedFact(_Strict):
    statement: str = Field(max_length=500, description="A fact stated by the cited records.")
    sources: list[SourceRef] = Field(min_length=1, max_length=6)


class Indicator(_Strict):
    description: str = Field(max_length=500)
    sources: list[SourceRef] = Field(min_length=1, max_length=6)


class EvidenceReference(_Strict):
    evidence_id: uuid.UUID = Field(description="Id of an evidence file attached to this case.")
    relevance: str = Field(max_length=400)
    excerpt: str | None = Field(
        default=None,
        max_length=400,
        description="Optional verbatim quote from the evidence's extracted text.",
    )


class InvestigationFindings(_Strict):
    summary: str = Field(max_length=1500)
    verified_facts: list[VerifiedFact] = Field(max_length=20)
    risk_indicators: list[Indicator] = Field(max_length=12)
    counter_indicators: list[Indicator] = Field(max_length=12)
    evidence_references: list[EvidenceReference] = Field(max_length=20)
    missing_information: list[str] = Field(max_length=12)
    limitations: list[str] = Field(max_length=12)
    recommended_action: RecommendedAction
    recommendation_rationale: str = Field(max_length=1200)
    human_approval_required: Literal[True] = Field(
        description="Always true: SENTINEL never acts on a recommendation without a human."
    )
