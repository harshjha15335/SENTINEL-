"""Database protection must survive accidental service-layer updates."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth.deps import Principal
from app.models import UserSession
from app.models.enums import DataOrigin, Role
from app.schemas.policy import PolicyParameters
from app.services import disputes, policy, refunds
from app.services.outbound import failure_diagnostic
from tests.phase4 import make_case


def actor(tenant, role=Role.ANALYST):
    return Principal(user=tenant.users[role], session=UserSession())


def test_refund_snapshot_amount_and_decision_are_database_immutable(db, tenant):
    case = make_case(db, tenant, origin=DataOrigin.SIMULATED)
    row = refunds.create(db, actor(tenant), case.id, amount_minor=100)
    identity = row.id
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text("update refund_requests set amount_minor=amount_minor+1 where id=:id"),
            {"id": identity},
        )
        db.commit()
    db.rollback()
    row = refunds.decide(
        db, actor(tenant, Role.ADMIN), identity, decision="APPROVED", digest=row.snapshot_sha256
    )
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text("update refund_requests set decided_by_role='ANALYST' where id=:id"),
            {"id": identity},
        )
        db.commit()
    db.rollback()


def test_shadow_policy_and_dispute_draft_content_cannot_be_rewritten(db, tenant):
    row = policy.create(
        db,
        actor(tenant),
        name="Shadow only",
        rationale="Review explicitly",
        params=PolicyParameters(),
    )
    identity = row.id
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text("update policy_drafts set rationale='replacement' where id=:id"), {"id": identity}
        )
        db.commit()
    db.rollback()
    case = make_case(db, tenant, origin=DataOrigin.SIMULATED)
    dispute = disputes.create_demo(db, actor(tenant), case.id, "ITEM_NOT_RECEIVED")
    draft = disputes.draft(db, actor(tenant), dispute.id)
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text("update dispute_drafts set body='fabricated' where id=:id"), {"id": draft.id}
        )
        db.commit()
    db.rollback()


def test_proxy_denial_is_separate_from_upstream_authorization():
    import httpx

    denied = failure_diagnostic(
        httpx.ProxyError("CONNECT denied 403; private body"),
        "https://user:password@project.supabase.co",
        "inbox_claim",
    )
    assert denied["upstream_reached"] is False and denied["proxy_status"] == 403
    assert "password" not in str(denied) and "private body" not in str(denied)
    req = httpx.Request("POST", "https://project.supabase.co")
    error = httpx.HTTPStatusError(
        "secret response", request=req, response=httpx.Response(403, request=req)
    )
    remote = failure_diagnostic(error, "https://project.supabase.co", "inbox_claim")
    assert remote["upstream_reached"] is True and remote["http_status"] == 403
    assert "secret response" not in str(remote)
