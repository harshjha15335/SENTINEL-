"""Bounded, provenance-scoped monitoring and investigation graph contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DataOrigin


class TimeWindow(BaseModel):
    start: datetime
    end: datetime


class CountPoint(BaseModel):
    date: str
    count: int


class ScoreBin(BaseModel):
    lower: float
    upper: float
    reference_count: int
    current_count: int


class FeatureComparison(BaseModel):
    feature: str
    reference_missing_rate: float | None
    current_missing_rate: float | None
    reference_mean: float | None
    current_mean: float | None


class MonitoringOut(BaseModel):
    observed_at: datetime
    data_origin: DataOrigin
    current_window: TimeWindow
    reference_window: TimeWindow
    transaction_volume: list[CountPoint]
    current_transactions: int
    reference_transactions: int
    current_scored: int
    reference_scored: int
    score_distribution: list[ScoreBin]
    risk_bands: dict[str, int]
    model_versions: dict[str, int]
    high_flag_rate: float | None
    illustrative_capacity: float
    capacity_utilization: float | None
    open_cases: int
    oldest_pending_hours: float | None
    overdue_cases: int
    case_growth: list[CountPoint]
    resolved_in_window: int
    resolution_rate: float | None
    confirmed_adverse_cases: int
    score_psi: float | None
    psi_note: str
    feature_comparison: list[FeatureComparison]
    sample_limit: int
    truncated: bool
    calibration_status: str
    limitations: list[str]


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    record_id: uuid.UUID | None = None
    risk_band: str | None = None
    source: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    explanation: str
    transaction_id: uuid.UUID
    data_origin: DataOrigin


class NetworkOut(BaseModel):
    data_origin: DataOrigin
    window: TimeWindow
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    repeated_payer_groups: int
    transaction_count: int
    limit: int
    truncated: bool
    limitations: list[str]
