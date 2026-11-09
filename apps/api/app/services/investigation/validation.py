"""Server-side checks that findings are grounded in the records the run actually read.

These run on every result (AI or deterministic) before it is saved. A failure means the output
is rejected, never partially saved.
"""

import re

from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import CaseToolbox

_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
# PayPal order/capture/payer ids (17 or 13 upper-case alphanumerics) and SENTINEL's own
# simulated/synthetic references.
_PROVIDER_ID = re.compile(r"\b(?:(?=[A-Z0-9]*\d)[A-Z0-9]{17}|(?:SIM|SYN)-[A-Z0-9][A-Z0-9-]{3,})\b")
# Claims that an external or financial action already happened. The agent has no such tools.
_ACTION_CLAIM = re.compile(
    r"\b(?:i|we|sentinel|the agent|the system)\s+(?:have\s+|has\s+)?"
    r"(?:issued|processed|initiated|executed|submitted|sent|filed|contacted|emailed|refunded|"
    r"blocked|cancell?ed|reversed|escalated to paypal)\b"
    r"|\b(?:refund|chargeback response|dispute response|evidence)\s+(?:has been|was)\s+"
    r"(?:issued|processed|submitted|sent|filed)\b",
    re.IGNORECASE,
)


class FindingsRejected(Exception):
    """The output cites, quotes or claims something the run cannot support."""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _texts(f: InvestigationFindings) -> list[str]:
    out = [f.summary, f.recommendation_rationale, *f.missing_information, *f.limitations]
    out += [x.statement for x in f.verified_facts]
    out += [x.description for x in f.risk_indicators + f.counter_indicators]
    out += [x.relevance for x in f.evidence_references]
    return out


def validate_findings(f: InvestigationFindings, box: CaseToolbox) -> None:
    problems: list[str] = []

    for group, items in (
        ("verified fact", [(x.statement, x.sources) for x in f.verified_facts]),
        ("risk indicator", [(x.description, x.sources) for x in f.risk_indicators]),
        ("counter-indicator", [(x.description, x.sources) for x in f.counter_indicators]),
    ):
        for _text, sources in items:
            for s in sources:
                if (s.kind.value, s.id) not in box.refs:
                    problems.append(
                        f"A {group} cites {s.kind.value} {s.id}, which this investigation did "
                        "not retrieve. Cite only ids returned by the tools."
                    )

    for ref in f.evidence_references:
        eid = str(ref.evidence_id)
        if ("evidence", eid) not in box.refs:
            problems.append(
                f"Evidence {eid} is not attached to this case or was not retrieved. Reference "
                "only evidence ids returned by list_case_evidence."
            )
            continue
        if ref.excerpt:
            source = box.evidence_text_read.get(eid)
            if source is None or _norm(ref.excerpt) not in _norm(source):
                problems.append(
                    f"The excerpt quoted for evidence {eid} does not appear in its text. Quote "
                    "verbatim from read_evidence_text, or omit the excerpt."
                )

    known = {i.lower() for i in box.identifiers}
    for text in _texts(f):
        for match in _UUID.findall(text) + _PROVIDER_ID.findall(text):
            if match.lower() not in known:
                problems.append(
                    f"The text mentions identifier {match}, which no tool returned. Do not "
                    "refer to payments or records that were not retrieved."
                )
        if _ACTION_CLAIM.search(text):
            problems.append(
                "The text claims an action was taken (for example a refund or submission). "
                "This investigation is read-only and took no action; describe recommendations "
                "only."
            )

    if problems:
        # De-duplicate while keeping order, and cap what goes back to the model.
        unique = list(dict.fromkeys(problems))[:8]
        raise FindingsRejected(" ".join(unique))
