"""Deterministic case summary used when no AI provider is available (or when asked for).

Built only from stored records through the same read-only toolbox the agent uses, so every fact
cites a real record. It is not AI-generated analysis and is labelled as such everywhere.
"""

from typing import Any

from app.services.investigation.schemas import (
    EvidenceReference,
    Indicator,
    InvestigationFindings,
    RecommendedAction,
    SourceKind,
    SourceRef,
    VerifiedFact,
)
from app.services.investigation.toolbox import PHASE5_UNAVAILABLE, CaseToolbox

DETERMINISTIC_LABEL = "Deterministic summary — AI provider unavailable"
DETERMINISTIC_CHOSEN_LABEL = "Deterministic summary — AI not used"


def _money(minor: int, currency: str) -> str:
    return f"{minor / 100:,.2f} {currency}"


def _ref(kind: SourceKind, rid: str) -> SourceRef:
    return SourceRef(kind=kind, id=rid)


def build_summary(box: CaseToolbox) -> InvestigationFindings:
    case = box.case_information()
    txn = box.transaction_details()
    risk = box.latest_risk_assessment()
    history = box.payer_history(limit=50)
    notes = box.case_notes()
    evidence = box.evidence_inventory()
    capture = box.capture_information()
    for name in ("get_graph_neighbors", "get_related_disputes", "get_merchant_policy"):
        box.unavailable(name)

    t_ref = _ref(SourceKind.TRANSACTION, txn["id"])
    facts = [
        VerifiedFact(
            statement=(
                f"Payment of {_money(txn['amount_minor'], txn['currency'])} with status "
                f"{txn['status']}; data origin {txn['data_origin']}. {txn['provenance_note']}"
            ),
            sources=[t_ref],
        ),
        VerifiedFact(
            statement=(
                f"Case is {case['status']} with {case['priority']} priority, opened by "
                f"{case['opened_by']}."
            ),
            sources=[_ref(SourceKind.CASE, case["id"])],
        ),
    ]
    if txn["refunded_at"]:
        facts.append(VerifiedFact(statement="This payment has a recorded refund.", sources=[t_ref]))
    if txn["disputed_at"]:
        facts.append(
            VerifiedFact(statement="This payment has a recorded dispute.", sources=[t_ref])
        )

    risk_ind: list[Indicator] = []
    counter: list[Indicator] = []
    limitations: list[str] = [
        "No AI analysis was performed. This summary restates stored records and the model's "
        "own explanation; it does not interpret documents.",
        f"Graph links, PayPal disputes and merchant policy checks: {PHASE5_UNAVAILABLE}",
    ]
    band = None
    if risk.get("available"):
        a_ref = _ref(SourceKind.RISK_ASSESSMENT, risk["id"])
        band = risk["risk_band"]
        facts.append(
            VerifiedFact(
                statement=(
                    f"Model {risk['model_version']} scored this payment {band} risk "
                    f"({risk['risk_score'] * 100:.1f}%). Shadow policy decision: "
                    f"{risk['policy_decision']} (recorded only, never enforced)."
                ),
                sources=[a_ref],
            )
        )
        for c in risk["top_contributions"]:
            text = (
                f"{c['label']} (value {c['value']:g}) moved the score "
                + ("up" if c["contribution_log_odds"] > 0 else "down")
                + f" by {abs(c['contribution_log_odds']):.2f} log-odds."
            )
            target = risk_ind if c["contribution_log_odds"] > 0 else counter
            if len(target) < 3 and abs(c["contribution_log_odds"]) >= 0.01:
                target.append(Indicator(description=text, sources=[a_ref]))
        limitations += list(risk["limitations"])[:6]
    else:
        limitations.append("This payment has no risk assessment.")

    if history.get("available"):
        payments: list[dict[str, Any]] = history["payments"]
        refunds = sum(1 for p in payments if p["refunded"])
        disputes = sum(1 for p in payments if p["disputed"])
        h_refs = [_ref(SourceKind.PAYER_HISTORY, p["id"]) for p in payments[:6]] or [t_ref]
        facts.append(
            VerifiedFact(
                statement=(
                    f"{len(payments)} earlier payment(s) from the same payer reference in the "
                    f"same data origin{' (at least; capped at 50)' if len(payments) >= 50 else ''}"
                    f"; {refunds} refunded, {disputes} disputed."
                ),
                sources=h_refs,
            )
        )
        if (refunds or disputes) and payments:
            risk_ind.append(
                Indicator(
                    description=f"Payer has {refunds} earlier refund(s) and {disputes} earlier "
                    "dispute(s) on record.",
                    sources=h_refs,
                )
            )
        elif payments:
            counter.append(
                Indicator(
                    description=f"Payer has {len(payments)} earlier payment(s) on record with "
                    "no refunds or disputes.",
                    sources=h_refs,
                )
            )

    events = capture["webhook_events"]
    if events:
        verified = sum(1 for e in events if e["verification"] == "VERIFIED")
        facts.append(
            VerifiedFact(
                statement=f"{len(events)} provider event(s) stored for this payment, "
                f"{verified} with a verified PayPal signature.",
                sources=[_ref(SourceKind.PAYMENT_EVENT, e["id"]) for e in events[:6]],
            )
        )

    ev_items = evidence["evidence"]
    refs = [
        EvidenceReference(
            evidence_id=e["id"],
            relevance=f"Attached by the merchant as {e['declared_category']} (uploader's label, "
            "not verified).",
        )
        for e in ev_items
    ]
    missing = [i["label"] for i in evidence["checklist"] if not i["provided"]]
    if notes["notes"]:
        facts.append(
            VerifiedFact(
                statement=f"{len(notes['notes'])} analyst note(s) on the case.",
                sources=[_ref(SourceKind.CASE_NOTE, n["id"]) for n in notes["notes"][:6]],
            )
        )

    if band == "HIGH" and not ev_items:
        action = RecommendedAction.REQUEST_MORE_EVIDENCE
        why = (
            "The model rates this payment high risk and no supporting evidence is attached. "
            "Collect the missing items before deciding."
        )
    elif band == "HIGH":
        action = RecommendedAction.CONTINUE_MANUAL_REVIEW
        why = (
            "The model rates this payment high risk. Evidence is attached but has not been "
            "interpreted by this summary; an analyst should review it."
        )
    elif ev_items and not missing:
        action = RecommendedAction.PREPARE_EVIDENCE_PACKET
        why = "The common evidence types are attached; an evidence packet can be prepared."
    else:
        action = RecommendedAction.CONTINUE_MANUAL_REVIEW
        why = "No rule-based signal is strong enough to recommend anything beyond review."

    summary = (
        f"{DETERMINISTIC_LABEL}. {_money(txn['amount_minor'], txn['currency'])} "
        f"{txn['status'].lower().replace('_', ' ')} payment ({txn['data_origin']})"
        + (f", scored {band} risk by the model in shadow mode" if band else ", not scored")
        + f". {len(ev_items)} evidence file(s) and {len(notes['notes'])} note(s) on the case."
    )
    return InvestigationFindings(
        summary=summary,
        verified_facts=facts[:20],
        risk_indicators=risk_ind,
        counter_indicators=counter,
        evidence_references=refs[:20],
        missing_information=missing,
        limitations=limitations[:12],
        recommended_action=action,
        recommendation_rationale=why,
        human_approval_required=True,
    )
