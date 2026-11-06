"""Typed operational views; no payloads, evidence text or credential values."""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DataOrigin


class StageCount(BaseModel):
    data_origin: DataOrigin
    status: str
    count: int


class WorkerStatus(BaseModel):
    name: str
    status: str
    fresh: bool
    heartbeat_at: datetime
    last_success_at: datetime | None
    last_successful_poll_at: datetime | None = None
    processed: int
    failures: int
    last_error: str | None


class InboxGroup(BaseModel):
    data_origin: DataOrigin
    status: str
    count: int
    oldest_received_at: datetime | None
    last_attempt_at: datetime | None


class InboxSnapshot(BaseModel):
    observed_at: datetime
    groups: list[InboxGroup]


class StorageStatus(BaseModel):
    backend: str
    database_query: str
    stored_files: int
    stored_bytes: int
    durability: str


class IntegrationStatus(BaseModel):
    paypal_mode: str
    paypal_credentials_configured: bool
    webhook_id_configured: bool
    last_verified_event_at: datetime | None
    ai_provider: str
    ai_configured: bool
    last_completed_ai_run_at: datetime | None
    verification_note: str


class OperationsOut(BaseModel):
    observed_at: datetime
    api: str
    ready: bool
    checks: dict[str, str]
    workers: list[WorkerStatus]
    events: list[StageCount]
    scoring_jobs: list[StageCount]
    investigations: list[StageCount]
    exhausted_events: int
    inbox_scope: str
    inbox_fresh: bool
    inbox: InboxSnapshot | None
    storage: StorageStatus
    integrations: IntegrationStatus
